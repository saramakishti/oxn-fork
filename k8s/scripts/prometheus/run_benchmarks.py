import os
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import subprocess
import time
import yaml
import requests

from config_prometheus import PrometheusConfig
from fault_detection_benchmark import PrometheusFaultDetection, FaultDetectionBenchmark

class BenchmarkAutomation:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.prometheus_config = PrometheusConfig()
        self.timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        
        # Create output directories
        self.results_dir = self.output_dir / f"benchmark_run_{self.timestamp}"
        self.prometheus_dir = self.results_dir / "prometheus_responses"
        self.csv_dir = self.results_dir / "csv_results"
        
        self._setup_directories()
    
    def _setup_directories(self):
        """Create necessary directories"""
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.prometheus_dir.mkdir(exist_ok=True)
        self.csv_dir.mkdir(exist_ok=True)
    
    def run_experiment(self, experiment_file: str, params: Dict) -> str:
        """Run a single experiment and return the report file path"""
        # Update Prometheus configuration if needed
        if 'prometheus' in params:
            self.prometheus_config.update_rules(**params['prometheus'])
            time.sleep(60)  # Wait for rules to apply
        
        # Create report directory
        report_dir = self.results_dir / "reports"
        report_dir.mkdir(exist_ok=True)
        
        # Run the experiment with OXN
        cmd = [
            "oxn",
            experiment_file,
            # Currently , there a a "bug" in oxn that requires that we pass in a / at the end of the report path
            "--report", str(report_dir) + "/",
            "--out-path", str(self.results_dir / "experiment_data"),
            "--out", "json,hdf",
            "--loglevel", "info",
            "--logfile", str(self.results_dir / "oxn.log")
        ]
        
        # Add any experiment-specific parameters
        #if 'experiment' in params:
        #    for key, value in params['experiment'].items():
        #        cmd.extend([f"--{key}", str(value)])
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Find the most recent report file
            report_files = list(report_dir.glob("report_*.yaml"))
            if not report_files:
                raise RuntimeError("No report file found after experiment")
            latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
            return str(latest_report)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Experiment failed: {e.stderr}")
    
    def analyze_results(self, experiment_file: str, report_file: str, run_params: Dict) -> List[Dict]:
        """Analyze experiment results and save data"""
        self.current_experiment = experiment_file
        
        # Get Prometheus data
        prometheus_file = self.prometheus_dir / f"prometheus_data_{self.timestamp}.json"
        
        # Download Prometheus alerts data
        try:
            # Port-forward Prometheus
            port_forward = subprocess.Popen([
                "kubectl", "port-forward",
                "-n", "system-under-evaluation",
                "svc/astronomy-shop-prometheus-server",
                "9090:9090"
            ])
            
            # Give port-forward time to establish
            time.sleep(2)
            
            # Query Prometheus
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)  # Get last hour of data
            
            params = {
                'query': 'ALERTS',
                'start': start_time.timestamp(),
                'end': end_time.timestamp(),
                'step': '15s'
            }
            
            response = requests.get(
                'http://localhost:9090/api/v1/query_range',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            # Save response to file
            with open(prometheus_file, 'w') as f:
                json.dump(response.json(), f, indent=2)
            
            # Clean up port-forward
            port_forward.terminate()
            port_forward.wait()
            
        except Exception as e:
            if 'port_forward' in locals():
                port_forward.terminate()
                port_forward.wait()
            raise RuntimeError(f"Failed to get Prometheus data: {e}")
        
        # Run analysis
        prometheus = PrometheusFaultDetection(str(prometheus_file))
        benchmark = FaultDetectionBenchmark(prometheus)
        results = benchmark.benchmark(report_file)
        
        # Add treatment information to results
        treatment_info = run_params.get('treatment', {})
        for result in results:
            result['fault_type'] = treatment_info.get('type', '')
            result['fault_params'] = treatment_info.get('params', {})
            result['fault_duration'] = treatment_info.get('duration', '')
        
        # Save results to CSV
        csv_file = self.csv_dir / f"results_{self.timestamp}.csv"
        self._save_to_csv(results, run_params, csv_file)
        
        return results
    
    def _save_to_csv(self, results: List[Dict], params: Dict, csv_file: Path):
        """Save benchmark results to CSV"""
        # Flatten prometheus and experiment params
        prometheus_params = params.get('prometheus', {})
        experiment_params = params.get('experiment', {})
        
        # Define columns
        fieldnames = [
            'timestamp',
            'fault_name',
            'fault_type',
            'fault_duration',
            'fault_params',
            'detected',
            'detection_latency',
            'first_alert',
            'all_alerts',
            'alert_count',
            'latency_threshold',
            'evaluation_window',
            'run_time',
            'timeout'
        ]
        
        with open(csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, 
                                  quoting=csv.QUOTE_NONNUMERIC,  # Quote all non-numeric fields
                                  escapechar='\\')              # Use backslash as escape character
            if f.tell() == 0:
                writer.writeheader()
            
            for result in results:
                # Extract treatment parameters
                fault_params = {}
                if result.get('fault_params'):
                    fault_params = result['fault_params'].copy()
                    duration = fault_params.pop('duration', None)
                    for common in ['namespace', 'label_selector', 'label', 'interface']:
                        fault_params.pop(common, None)
                
                # Format all alerts
                all_alerts = []
                if result['detected']:
                    for alert in result['alerts_triggered']:
                        all_alerts.append({
                            'name': alert['name'],
                            'time': alert['time'].strftime('%Y-%m-%d %H:%M:%S'),
                            'severity': alert['severity'],
                            'service': alert['labels'].get('job', 'N/A'),
                            'rpc_service': alert['labels'].get('rpc_service', ''),
                            'rpc_method': alert['labels'].get('rpc_method', '')
                        })
                
                # Convert JSON to strings with proper escaping
                fault_params_str = json.dumps(fault_params) if fault_params else None
                all_alerts_str = json.dumps(all_alerts) if all_alerts else None
                
                row = {
                    'timestamp': self.timestamp,
                    'fault_name': result['fault_name'],
                    'fault_type': result.get('fault_type', ''),
                    'fault_duration': duration if duration else None,
                    'fault_params': fault_params_str,
                    'detected': result['detected'],
                    'detection_latency': result['detection_latency'] if result['detected'] else None,
                    'first_alert': result['alerts_triggered'][0]['name'] if result['detected'] else None,
                    'all_alerts': all_alerts_str,
                    'alert_count': len(result['alerts_triggered']) if result['detected'] else 0,
                    'latency_threshold': prometheus_params.get('latency_threshold'),
                    'evaluation_window': prometheus_params.get('evaluation_window'),
                    'run_time': experiment_params.get('run_time'),
                    'timeout': experiment_params.get('timeout')
                }
                writer.writerow(row)

def setup_helm():
    """Setup Helm repositories"""
    try:
        # Add OpenTelemetry Helm repo
        subprocess.run([
            "helm", "repo", "add",
            "open-telemetry",
            "https://open-telemetry.github.io/opentelemetry-helm-charts"
        ], check=True)
        
        # Update repos
        subprocess.run(["helm", "repo", "update"], check=True)
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to setup Helm: {e.stderr}")

def main():
    # Setup Helm first
    setup_helm()
    
    # Configuration
    EXPERIMENTS = {
        'package-loss-15': {
            'file': '/opt/oxn/experiments/package-loss-15.yml',
            'variations': [
                {
                    'prometheus': {
                        'latency_threshold': threshold,
                        'evaluation_window': window
                    },
                    'experiment': {
                        'times': 1,
                        'timeout': '5m'
                    },
                    'treatment': {
                        'type': 'kubernetes_loss',
                        'duration': '4m',
                        'params': {
                            'loss_percentage': 15.0,
                            'namespace': 'system-under-evaluation',
                            'label_selector': 'app.kubernetes.io/name',
                            'label': 'astronomy-shop-recommendationservice',
                            'interface': 'eth0'
                        }
                    }
                }
                for threshold in [100, 200, 300, 400]
                for window in ['10s', '20s', '30s', '40s']
            ]
        },
        'package-loss-20': {
            'file': '/opt/oxn/experiments/package-loss-20.yml',
            'variations': [
                {
                    'prometheus': {
                        'latency_threshold': threshold,
                        'evaluation_window': window
                    },
                    'experiment': {
                        'times': 1,
                        'timeout': '5m'
                    },
                    'treatment': {
                        'type': 'kubernetes_loss',
                        'duration': '4m',
                        'params': {
                            'loss_percentage': 20.0,
                            'namespace': 'system-under-evaluation',
                            'label_selector': 'app.kubernetes.io/name',
                            'label': 'astronomy-shop-recommendationservice',
                            'interface': 'eth0'
                        }
                    }
                }
                for threshold in [100, 200, 300, 400]
                for window in ['10s', '20s', '30s', '40s']
            ]
        },
        'package-loss-20-short': {
            'file': '/opt/oxn/experiments/package-loss-20-short.yml',
            'variations': [
                {
                    'prometheus': {
                        'latency_threshold': threshold,
                        'evaluation_window': window
                    },
                    'experiment': {
                        'times': 1,
                        'timeout': '5m'
                    },
                    'treatment': {
                        'type': 'kubernetes_loss',
                        'duration': '2m',
                        'params': {
                            'loss_percentage': 20.0,
                            'namespace': 'system-under-evaluation',
                            'label_selector': 'app.kubernetes.io/name',
                            'label': 'astronomy-shop-recommendationservice',
                            'interface': 'eth0'
                        }
                    }
                }
                for threshold in [100, 200, 300, 400]
                for window in ['10s', '20s', '30s', '40s']
            ]
        },
        
        'delay-120': {
            'file': '/opt/oxn/experiments/delay-120.yml',
            'variations': [
                {
                    'prometheus': {
                        'latency_threshold': threshold,
                        'evaluation_window': window
                    },
                    'experiment': {
                        'times': 1,
                        'timeout': '5m'
                    },
                    'treatment': {
                        'type': 'delay',
                        'duration': '2m',
                        'params': {
                            'delay_time': '120ms',
                            'delay_jitter': '120ms',
                            'namespace': 'system-under-evaluation',
                            'label_selector': 'app.kubernetes.io/name',
                            'label': 'astronomy-shop-recommendationservice',
                            'interface': 'eth0'
                        }
                    }
                }
                for threshold in [100, 200, 300, 400]
                for window in ['10s', '20s', '30s', '40s']
            ]
        },
        'delay-90': {
            'file': '/opt/oxn/experiments/delay-90.yml',
            'variations': [
                {
                    'prometheus': {
                        'latency_threshold': threshold,
                        'evaluation_window': window
                    },
                    'experiment': {
                        'times': 1,
                        'timeout': '5m'
                    },
                    'treatment': {
                        'type': 'delay',
                        'duration': '2m',
                        'params': {
                            'delay_time': '90ms',
                            'delay_jitter': '90ms',
                            'namespace': 'system-under-evaluation',
                            'label_selector': 'app.kubernetes.io/name',
                            'label': 'astronomy-shop-recommendationservice',
                            'interface': 'eth0'
                        }
                    }
                }
                for threshold in [100, 200, 300, 400]
                for window in ['10s', '20s', '30s', '40s']
            ]
        },
        'delay-90-45': {
            'file': '/opt/oxn/experiments/delay-90-45.yml',
            'variations': [
                {
                    'prometheus': {
                        'latency_threshold': threshold,
                        'evaluation_window': window
                    },
                    'experiment': {
                        'times': 1,
                        'timeout': '5m'
                    },
                    'treatment': {
                        'type': 'delay',
                        'duration': '2m',
                        'params': {
                            'delay_time': '90ms',
                            'delay_jitter': '45ms',
                            'namespace': 'system-under-evaluation',
                            'label_selector': 'app.kubernetes.io/name',
                            'label': 'astronomy-shop-recommendationservice',
                            'interface': 'eth0'
                        }
                    }
                }
                for threshold in [100, 200, 300, 400]
                for window in ['10s', '20s', '30s', '40s']
            ]
        },
    }
    
    OUTPUT_DIR = "/opt/oxn/benchmark_results"
    
    # Run benchmarks
    automation = BenchmarkAutomation(OUTPUT_DIR)
    
    for exp_name, exp_config in EXPERIMENTS.items():
        for variation in exp_config['variations']:
            try:
                # Run experiment
                report_file = automation.run_experiment(exp_config['file'], variation)
                
                # Analyze results
                results = automation.analyze_results(
                    exp_config['file'],
                    report_file,
                    variation
                )
                
                print(f"Completed run for {exp_name} with params: {variation}")
                time.sleep(60)  # Cool-down period between runs
                
            except Exception as e:
                print(f"Error running {exp_name} with params {variation}: {e}")
                continue

if __name__ == "__main__":
    main() 