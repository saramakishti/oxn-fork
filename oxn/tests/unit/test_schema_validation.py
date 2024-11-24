import unittest
import json
import os
import yaml
from jsonschema import validate

from oxn.validation import load_schema
from oxn.errors import OxnException

class SchemaValidationTest(unittest.TestCase):
    def setUp(self):
        self.schema = load_schema()
        self.valid_spec = {
            "experiment": {
                "name": "k8s-test-successful",
                "version": "0.0.1",
                "orchestrator": "kubernetes",
                "services": {
                    "jaeger": {
                        "name": "astronomy-shop-jaeger-query",
                        "namespace": "system-under-evaluation"
                    },
                    "prometheus": [
                        {
                            "name": "astronomy-shop-prometheus-server",
                            "namespace": "system-under-evaluation",
                            "target": "sue"
                        },
                        {
                            "name": "kube-prometheus-kube-prome-prometheus", 
                            "namespace": "oxn-external-monitoring",
                            "target": "oxn"
                        }
                    ]
                },
                "responses": [
                    {
                        "name": "frontend_traces",
                        "type": "trace", 
                        "service_name": "frontend",
                        "left_window": "60s",
                        "right_window": "60s",
                        "target": "sue",
                        "limit": 10000
                    },
                    {
                        "name": "shippingservice_traces",
                        "type": "trace",
                        "service_name": "shippingservice", 
                        "left_window": "60s",
                        "right_window": "60s",
                        "limit": 10000
                    },
                    {
                        "name": "system_CPU",
                        "type": "metric",
                        "metric_name": "sum(rate(container_cpu_usage_seconds_total{namespace=\"system-under-evaluation\"}[1m]))",
                        "left_window": "60s",
                        "right_window": "60s",
                        "step": 1,
                        "target": "oxn"
                    },
                    {
                        "name": "latency_recommendationservice_95_percentile",
                        "type": "metric",
                        "metric_name": "histogram_quantile(0.95, sum(rate(duration_milliseconds_bucket{service_name=\"recommendationservice\"}[90s])) by (le))",
                        "left_window": "300s",
                        "right_window": "300s",
                        "step": 1,
                        "target": "sue"
                    }
                ],
                "treatments": [
                    {
                        "empty_treatment": {
                            "action": "empty",
                            "params": {"duration": "1m"}
                        }
                    }
                ],
                "sue": {
                    "compose": "opentelemetry-demo/docker-compose.yml",
                    "exclude": ["loadgenerator"],
                    "required": [
                        {
                            "namespace": "system-under-evaluation",
                            "name": "astronomy-shop-prometheus-server"
                        }
                    ]
                },
                "loadgen": {
                    "run_time": "2m",
                    "max_users": 10,
                    "spawn_rate": 5,
                    "locust_files": [
                        "/opt/oxn/locust/locust_basic_interaction.py",
                        "/opt/oxn/locust/locust_otel_demo.py"
                    ],
                    "target": {
                        "name": "astronomy-shop-frontendproxy",
                        "namespace": "system-under-evaluation",
                        "port": 8080
                    }
                }
            }
        }

    def test_valid_experiment_spec(self):
        """Test that a valid experiment spec passes validation"""
        # Should not raise an exception
        validate(instance=self.valid_spec, schema=self.schema)

    def test_invalid_experiment_spec(self):
        """Test that an invalid experiment spec fails validation"""
        invalid_spec = {
            "experiment": {
                # Missing required fields
                "responses": []
            }
        }
        
        with self.assertRaises(Exception):
            validate(instance=invalid_spec, schema=self.schema)

    def test_real_experiment_files(self):
        """Test that our actual experiment files pass validation"""
        experiments_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'experiments')
        
        for filename in os.listdir(experiments_dir):
            if filename.endswith('.yml') or filename.endswith('.yaml'):
                with open(os.path.join(experiments_dir, filename)) as f:
                    spec = yaml.safe_load(f)
                    try:
                        validate(instance=spec, schema=self.schema)
                    except Exception as e:
                        self.fail(f"Validation failed for {filename}: {str(e)}")