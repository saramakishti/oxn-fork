import subprocess
import yaml
import tempfile
from pathlib import Path
from typing import Dict, Optional

class HelmUpgradeError(Exception):
    """Raised when helm upgrade fails"""
    pass

class PrometheusConfig:
    # Constant rules that should always be present
    # This is a subset of the rules in the default config
    # Some of them are not relevant and bloat our rules
    PERMANENT_RULES = {
        'name': 'PrometheusKubernetesAlerts',
        'rules': [
            {
                'alert': 'PrometheusJobMissing',
                'expr': 'absent(up{job="prometheus"})',
                'for': '0m',
                'labels': {'severity': 'warning'},
                'annotations': {
                    'summary': 'Prometheus job missing (instance {{ $labels.instance }})',
                    'description': 'A Prometheus job has disappeared\n  VALUE = {{ $value }}\n  LABELS = {{ $labels }}'
                }
            },
            {
                'alert': 'PrometheusTargetMissing',
                'expr': 'up == 0',
                'for': '0m',
                'labels': {'severity': 'critical'},
                'annotations': {
                    'summary': 'Prometheus target missing (instance {{ $labels.instance }})',
                    'description': 'A Prometheus target has disappeared. An exporter might be crashed.\n  VALUE = {{ $value }}\n  LABELS = {{ $labels }}'
                }
            },
            {
                'alert': 'PrometheusConfigurationReloadFailure',
                'expr': 'prometheus_config_last_reload_successful != 1',
                'for': '0m',
                'labels': {'severity': 'warning'},
                'annotations': {
                    'summary': 'Prometheus configuration reload failure (instance {{ $labels.instance }})',
                    'description': 'Prometheus configuration reload error\n  VALUE = {{ $value }}\n  LABELS = {{ $labels }}'
                }
            },
            {
                'alert': 'PrometheusRuleEvaluationSlow',
                'expr': 'prometheus_rule_group_last_duration_seconds > prometheus_rule_group_interval_seconds',
                'for': '5m',
                'labels': {'severity': 'warning'},
                'annotations': {
                    'summary': 'Prometheus rule evaluation slow (instance {{ $labels.instance }})',
                    'description': 'Prometheus rule evaluation took more time than the scheduled interval. It indicates a slower storage backend access or too complex query.\n  VALUE = {{ $value }}\n  LABELS = {{ $labels }}'
                }
            },
            {
                'alert': 'PrometheusTargetScrapingSlow',
                'expr': 'prometheus_target_interval_length_seconds{quantile="0.9"} / on (interval, instance, job) prometheus_target_interval_length_seconds{quantile="0.5"} > 1.05',
                'for': '5m',
                'labels': {'severity': 'warning'},
                'annotations': {
                    'summary': 'Prometheus target scraping slow (instance {{ $labels.instance }})',
                    'description': 'Prometheus is scraping exporters slowly since it exceeded the requested interval time. Your Prometheus server is under-provisioned.\n  VALUE = {{ $value }}\n  LABELS = {{ $labels }}'
                }
            },
            {
                'alert': 'KubernetesNodeNotReady',
                'expr': 'kube_node_status_condition{condition="Ready",status="true"} == 0',
                'for': '10m',
                'labels': {'severity': 'critical'},
                'annotations': {
                    'summary': 'Kubernetes Node ready (node {{ $labels.node }})',
                    'description': 'Node {{ $labels.node }} has been unready for a long time\n  VALUE = {{ $value }}\n  LABELS = {{ $labels }}'
                }
            },
            {
                'alert': 'KubernetesNodeMemoryPressure', 
                'expr': 'kube_node_status_condition{condition="MemoryPressure",status="true"} == 1',
                'for': '2m',
                'labels': {'severity': 'critical'},
                'annotations': {
                    'summary': 'Kubernetes memory pressure (node {{ $labels.node }})',
                    'description': 'Node {{ $labels.node }} has MemoryPressure condition\n  VALUE = {{ $value }}\n  LABELS = {{ $labels }}'
                }
            },
            {
                'alert': 'KubernetesNodeDiskPressure',
                'expr': 'kube_node_status_condition{condition="DiskPressure",status="true"} == 1',
                'for': '2m', 
                'labels': {'severity': 'critical'},
                'annotations': {
                    'summary': 'Kubernetes disk pressure (node {{ $labels.node }})',
                    'description': 'Node {{ $labels.node }} has DiskPressure condition\n  VALUE = {{ $value }}\n  LABELS = {{ $labels }}'
                }
            },
            {
                'alert': 'KubernetesNodeNetworkUnavailable',
                'expr': 'kube_node_status_condition{condition="NetworkUnavailable",status="true"} == 1',
                'for': '2m',
                'labels': {'severity': 'critical'},
                'annotations': {
                    'summary': 'Kubernetes Node network unavailable (instance {{ $labels.instance }})',
                    'description': 'Node {{ $labels.node }} has NetworkUnavailable condition\n  VALUE = {{ $value }}\n  LABELS = {{ $labels }}'
                }
            },
            {
                'alert': 'KubernetesNodeOutOfPodCapacity',
                'expr': 'sum by (node) ((kube_pod_status_phase{phase="Running"} == 1) + on(uid) group_left(node) (0 * kube_pod_info{pod_template_hash=""})) / sum by (node) (kube_node_status_allocatable{resource="pods"}) * 100 > 90',
                'for': '2m',
                'labels': {'severity': 'warning'},
                'annotations': {
                    'summary': 'Kubernetes Node out of pod capacity (instance {{ $labels.instance }})',
                    'description': 'Node {{ $labels.node }} is out of pod capacity\n  VALUE = {{ $value }}\n  LABELS = {{ $labels }}'
                }
            },
            {
                'alert': 'KubernetesContainerOomKiller',
                'expr': '(kube_pod_container_status_restarts_total - kube_pod_container_status_restarts_total offset 10m >= 1) and ignoring (reason) min_over_time(kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}[10m]) == 1',
                'for': '0m',
                'labels': {'severity': 'warning'},
                'annotations': {
                    'summary': 'Kubernetes container oom killer ({{ $labels.namespace }}/{{ $labels.pod }}:{{ $labels.container }})',
                    'description': 'Container {{ $labels.container }} in pod {{ $labels.namespace }}/{{ $labels.pod }} has been OOMKilled {{ $value }} times in the last 10 minutes.\n  VALUE = {{ $value }}\n  LABELS = {{ $labels }}'
                }
            }
        ],
    }

    def __init__(self, namespace: str = 'system-under-evaluation'):
        self.namespace = namespace
        
    def _restart_prometheus(self):
        """Restart the Prometheus pod to apply new rules"""
        try:
            # Get prometheus pod name
            cmd = [
                "kubectl", "get", "pods",
                "-n", self.namespace,
                "-l", "app.kubernetes.io/instance=astronomy-shop,app.kubernetes.io/name=prometheus",
                "-o", "jsonpath='{.items[0].metadata.name}'"
            ]
            pod_name = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip("'")
            
            # Delete the pod (it will be automatically recreated)
            subprocess.run([
                "kubectl", "delete", "pod",
                "-n", self.namespace,
                pod_name
            ], check=True)
            
            # Wait for new pod to be ready
            subprocess.run([
                "kubectl", "wait", "--for=condition=ready", "pod",
                "-n", self.namespace,
                "-l", "app.kubernetes.io/instance=astronomy-shop,app.kubernetes.io/name=prometheus",
                "--timeout=60s"
            ], check=True)
            
        except subprocess.CalledProcessError as e:
            raise HelmUpgradeError(f"Failed to restart Prometheus: {e.stderr}")

    def _create_values_file(self, latency_threshold: Optional[int] = None, 
                           evaluation_window: Optional[str] = None) -> str:
        """Create a temporary values file for helm upgrade"""
        values = {
            'prometheus': {
                'serverFiles': {
                    'alerting_rules.yml': {
                        'groups': [
                            # Permanent monitoring rules
                            self.PERMANENT_RULES,
                            # HTTP Latency Alert
                            {
                                'name': 'astronomy-shop-rapid-http-latency-alerts',
                                'rules': [{
                                    'alert': 'ImmediateHighHTTPLatency',
                                    'expr': f'histogram_quantile(0.95, sum(rate(http_server_duration_milliseconds_bucket{{job=~"opentelemetry-demo/.*", http_status_code="200",le!="infinity"}}[90s])) by (job, http_method, http_flavor, net_host_name, le)) > {latency_threshold}' if latency_threshold else None,
                                    'for': evaluation_window if evaluation_window else None
                                }]
                            },
                            # RPC Latency Alert
                            {
                                'name': 'astronomy-shop-rapid-rpc-latency-alerts',
                                'rules': [{
                                    'alert': 'ImmediateHighRPCLatency',
                                    'expr': f'histogram_quantile(0.95, sum(rate(rpc_server_duration_milliseconds_bucket{{job=~"opentelemetry-demo/.*", rpc_grpc_status_code="0",le!="infinity"}}[90s])) by (job, rpc_method, rpc_service, le)) > {latency_threshold}' if latency_threshold else None,
                                    'for': evaluation_window if evaluation_window else None
                                }]
                            },
                            # Critical Service RPC Latency Alert
                            {
                                'name': 'astronomy-shop-critical-service-rpc-latency',
                                'rules': [{
                                    'alert': 'CriticalServiceRPCLatencySpike',
                                    'expr': f'histogram_quantile(0.95, sum by (job, rpc_method, rpc_service, le) (rate(rpc_server_duration_milliseconds_bucket{{job=~"opentelemetry-demo/(checkoutservice|adservice|productcatalogservice)",le!="infinity",rpc_grpc_status_code="0"}}[90s]))) > {latency_threshold}' if latency_threshold else None,
                                    'for': evaluation_window if evaluation_window else None
                                }]
                            }
                        ]
                    }
                }
            }
        }
        
        # Remove None values
        def clean_dict(d):
            if not isinstance(d, dict):
                return d
            return {k: clean_dict(v) for k, v in d.items() if v is not None}
        
        values = clean_dict(values)
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(values, temp_file, default_flow_style=False)
        temp_file.close()
        return temp_file.name

    def update_rules(
        self,
        latency_threshold: Optional[int] = None,
        evaluation_window: Optional[str] = None,
        dry_run: bool = False
    ) -> str:
        """Update Prometheus alert rules via helm upgrade"""
        try:
            values_file = self._create_values_file(latency_threshold, evaluation_window)
            
            cmd = [
                "helm", "upgrade",
                "astronomy-shop",
                "open-telemetry/opentelemetry-demo",
                "--namespace", self.namespace,
                "--reuse-values",
                "-f", values_file
            ]
            
            if dry_run:
                cmd.append("--dry-run")
            
            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                raise HelmUpgradeError(f"Helm upgrade failed:\n{e.stderr}")
            
            if not dry_run:
                self._restart_prometheus()
            
            Path(values_file).unlink()
            return result.stdout
            
        except Exception as e:
            if 'values_file' in locals():
                Path(values_file).unlink()
            raise HelmUpgradeError(f"Error updating rules: {str(e)}")

    def get_current_rules(self) -> Dict:
        """Get current Prometheus rules configuration"""
        cmd = [
            "helm", "get", "values",
            "astronomy-shop",
            "--namespace", self.namespace,
            "-o", "yaml"
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            values = yaml.safe_load(result.stdout)
            return values.get('prometheus', {}).get('serverFiles', {}).get('alerting_rules.yml', {})
        except subprocess.CalledProcessError as e:
            raise HelmUpgradeError(f"Failed to get values:\n{e.stderr}")