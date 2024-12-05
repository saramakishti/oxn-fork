import requests
import json
import time
from datetime import datetime, timedelta
import subprocess
import sys
import signal
import logging
from collections import defaultdict
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
JAEGER_BASE_URL = "http://localhost:8080/jaeger/ui/api"
PROMETHEUS_BASE_URL = "http://localhost:9090/api/v1"
CHECK_INTERVAL = 10  # seconds
RUNTIME_DURATION = timedelta(minutes=1)  # How long to run the script for (None for infinite)
LOOKBACK_WINDOW = {
    'prometheus': timedelta(minutes=5),  # How far back to look for Prometheus metrics
    'jaeger': timedelta(hours=1)        # How far back to look for Jaeger traces
}

########################### PROMETHEUS ###########################
# Define metrics to monitor
PROMETHEUS_METRICS = [
    # Pod Health Metrics
    {
        'name': 'Pod Status Phases',
        'query': 'sum by (phase) (kube_pod_status_phase{namespace="system-under-evaluation"})'
    },
    {
        'name': 'Pod Restarts',
        'query': 'sum(kube_pod_container_status_restarts_total{namespace="system-under-evaluation"})'
    },
    {
        'name': 'Terminated Pods',
        'query': 'sum(kube_pod_container_status_terminated{namespace="system-under-evaluation"})'
    },

    # Network Performance Metrics
    {
        'name': 'Failed Spans',
        'query': 'sum(rate(otelcol_exporter_send_failed_spans[1m]))'
    },
    {
        'name': 'Network Receive Bytes',
        'query': 'sum(rate(node_network_receive_bytes_total[1m])) by (instance)'
    },
    {
        'name': 'Network Transmit Bytes',
        'query': 'sum(rate(node_network_transmit_bytes_total[1m])) by (instance)'
    },

    # Packet Loss Metrics
    {
        'name': 'Network Drops',
        'query': 'sum(rate(node_network_receive_drop_total[1m]) + rate(node_network_transmit_drop_total[1m])) by (instance)'
    },
    {
        'name': 'Network Errors',
        'query': 'sum(rate(node_network_receive_errs_total[1m]) + rate(node_network_transmit_errs_total[1m])) by (instance)'
    },
    {
        'name': 'TCP Retransmissions',
        'query': 'sum(rate(node_netstat_Tcp_RetransSegs[1m])) by (instance)'
    },
    {
        'name': 'TCP/UDP Errors',
        'query': 'sum(rate(node_netstat_Tcp_InErrs[1m]) + rate(node_netstat_Udp_InErrors[1m])) by (instance)'
    },

    # System Health Metrics
    {
        'name': 'Node Load Average',
        'query': 'node_load1'
    },
    {
        'name': 'Memory Available',
        'query': 'node_memory_MemAvailable_bytes'
    },
    {
        'name': 'CPU Usage',
        'query': 'sum(rate(node_cpu_seconds_total{mode!="idle"}[1m])) by (instance)'
    },
    {
        'name': 'TCP Connections',
        'query': 'node_netstat_Tcp_CurrEstab'
    },

    # latency metrics
    ################### important : 90s AT LEAST #################
    {
        'name': 'Frontend HTTP Latency (p95)',
        'query': 'histogram_quantile(0.95, sum(rate(http_server_duration_milliseconds_bucket{job="opentelemetry-demo/frontend"}[90s])) by (http_method, http_status_code, le))'
    },
    {
        'name': 'Cart Service HTTP Latency (p95)',
        'query': 'histogram_quantile(0.95, sum(rate(http_server_request_duration_seconds_bucket{job="opentelemetry-demo/cartservice"}[90s])) by (http_route, le)) * 1000'
    },
    {
        'name': 'Product Catalog RPC Latency (p95)',
        'query': 'histogram_quantile(0.95, sum(rate(rpc_server_duration_milliseconds_bucket{job="opentelemetry-demo/productcatalogservice"}[90s])) by (rpc_method, le))'
    },
    {
        'name': 'Ad Service RPC Client Latency (p95)',
        'query': 'histogram_quantile(0.95, sum(rate(rpc_client_duration_milliseconds_bucket{job="opentelemetry-demo/adservice"}[90s])) by (rpc_method, rpc_service, le))'
    }
]

########################### JAEGER ###########################
# services to monitor traces for
JAEGER_SERVICES = [
    'frontend',
    'recommendationservice',
    'productcatalogservice',
    'cartservice',
    'checkoutservice',
    'currencyservice',
    'paymentservice',
    'shippingservice'
]

class MetricsStats:
    def __init__(self):
        self.total_checks = defaultdict(int)
        self.failed_checks = defaultdict(int)
        self.start_time = datetime.now()
    
    def record_check(self, name: str, success: bool):
        self.total_checks[name] += 1
        if not success:
            self.failed_checks[name] += 1
    
    def get_summary(self) -> str:
        runtime = datetime.now() - self.start_time
        summary = [
            f"\nMonitoring Summary (Runtime: {str(runtime).split('.')[0]})",
            "-" * 50
        ]
        
        for name in self.total_checks.keys():
            total = self.total_checks[name]
            failed = self.failed_checks[name]
            success_rate = ((total - failed) / total) * 100 if total > 0 else 0
            status = "✅" if failed == 0 else "❌"
            summary.append(
                f"{name} {status}:\n"
                f"  Total Checks: {total}\n" 
                f"  Failed Checks: {failed}\n"
                f"  Success Rate: {success_rate:.1f}%"
            )
        
        return "\n".join(summary)

class PortForwarder:
    def __init__(self):
        self.processes = []
        
    def start(self) -> bool:
        """Setup required port-forwards"""
        try:
            prometheus_forward = subprocess.Popen(
                ["kubectl", "port-forward", 
                "-n", "system-under-evaluation",
                "svc/astronomy-shop-prometheus-server",
                "9090:9090"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            frontend_forward = subprocess.Popen(
                ["kubectl", "port-forward",
                "-n", "system-under-evaluation",
                "svc/astronomy-shop-frontendproxy",
                "8080:8080"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.processes = [prometheus_forward, frontend_forward]
            time.sleep(5)
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup port-forwards: {e}")
            self.cleanup()
            return False

    def cleanup(self):
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        self.processes = []

def check_prometheus_metric(metric_query: str) -> Tuple[bool, str]:
    """Query Prometheus and check if we get valid data"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)
        
        params = {
            'query': metric_query,
            'start': start_time.timestamp(),
            'end': end_time.timestamp(),
            'step': '15s'
        }
        
        response = requests.get(
            f"{PROMETHEUS_BASE_URL}/query_range", 
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        if data['status'] == 'success' and len(data['data']['result']) > 0:
            return True, "Data received"
        return False, "No data points found"
    
    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection failed"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_jaeger_traces(service_name: str) -> Tuple[bool, str]:
    """Query Jaeger for traces from a specific service"""
    try:
        end_time = int(datetime.now().timestamp() * 1_000_000)  # microseconds
        start_time = int((datetime.now() - timedelta(hours=1)).timestamp() * 1_000_000)
        
        params = {
            'service': service_name,
            'limit': 20,
            'lookback': '1h',
            'start': start_time,
            'end': end_time
        }
        
        response = requests.get(
            f"{JAEGER_BASE_URL}/traces", 
            params=params,
            timeout=10
        )
        
        if not response.text.strip():
            return False, "Empty response from Jaeger"
            
        try:
            response.raise_for_status()
            data = response.json()
        except json.JSONDecodeError:
            return False, "Invalid JSON response"
        except requests.exceptions.HTTPError as e:
            return False, f"HTTP error: {e}"
            
        if data and len(data.get('data', [])) > 0:
            return True, f"Found {len(data['data'])} traces"
        return False, "No traces found"
    
    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection failed"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_metrics(stats: MetricsStats):
    """Run one iteration of metric checks"""
    logger.debug(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    
    # Check Prometheus metrics
    logger.debug("\nChecking Prometheus metrics...")
    for metric in PROMETHEUS_METRICS:
        success, message = check_prometheus_metric(metric['query'])
        stats.record_check(f"Prometheus - {metric['name']}", success)
        if success:
            logger.debug(f"✅ {metric['name']}: {message}")
        else:
            logger.info(f"❌ {metric['name']}: {message}")
    
    # Check Jaeger traces
    logger.debug("\nChecking Jaeger traces...")
    for service in JAEGER_SERVICES:
        success, message = check_jaeger_traces(service)
        stats.record_check(f"Jaeger - {service}", success)
        if success:
            logger.debug(f"✅ {service}: {message}")
        else:
            logger.info(f"❌ {service}: {message}")

def main():
    # Flag for graceful shutdown
    running = True
    forwarder = PortForwarder()
    
    def signal_handler(signum, frame):
        nonlocal running
        running = False
        print("\nStopping monitoring...")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Setting up port-forwards...")
    if not forwarder.start():
        sys.exit(1)
    
    stats = MetricsStats()
    start_time = datetime.now()
    
    try:
        print("\nStarting continuous monitoring...")
        print("Only showing errors (failed checks)...")
        
        while running:
            try:
                # Check if runtime duration has elapsed
                if RUNTIME_DURATION and (datetime.now() - start_time) >= RUNTIME_DURATION:
                    print("\nRuntime duration reached.")
                    break
                
                check_metrics(stats)
                time.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"\nError during metric check: {e}")
                logger.info(f"Retrying in {CHECK_INTERVAL} seconds...")
                time.sleep(CHECK_INTERVAL)
                
    finally:
        print(stats.get_summary())
        print("\nCleaning up port-forwards...")
        forwarder.cleanup()

if __name__ == "__main__":
    main()