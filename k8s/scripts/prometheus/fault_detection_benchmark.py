from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
import yaml
import requests
import json
from typing import Dict, List, Optional, Union
import logging
from pathlib import Path
from collections import defaultdict

######################NOTES######################
# There is a maximum resolution for the time series data from Prometheus alerts.
# From experience, it's 8 seconds. This is expressed in the 'step' parameter in the
# query_range call.
# {"status":"error","errorType":"bad_data","error":"exceeded maximum resolution of 11,000 points per timeseries. Try decreasing the query resolution (?step=XX)"}

# Somehow the prometheus timestamp is always 1 hour behind the actual time.
#################################################


# Configure root logger
logger = logging.getLogger()  # Root logger
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Get module logger
module_logger = logging.getLogger(__name__)

@dataclass
class InjectedFault:
    """Represents a fault that was injected"""
    name: str
    start_time: datetime
    end_time: datetime
    type: str
    params: Dict

@dataclass
class DetectionEvent:
    """Represents a detection of a fault"""
    alert_name: str
    firing_time: datetime
    severity: str
    labels: Dict

class FaultDetectionMechanism(ABC):
    """Abstract base class for fault detection mechanisms"""
    
    @abstractmethod
    def get_detections(self, start_time: datetime, end_time: datetime) -> List[DetectionEvent]:
        """Get all fault detections in the given time window"""
        pass

class PrometheusFaultDetection(FaultDetectionMechanism):
    """Prometheus-based fault detection implementation"""
    
    def __init__(self, source: Union[str, Path]):
        self.source = str(source)
        self.is_file = not self.source.startswith(('http://', 'https://'))
        self.logger = logging.getLogger(__name__)
    
    def _process_alert_results(self, data: dict, start_time: datetime, end_time: datetime) -> List[DetectionEvent]:
        """Process alert results from either file or Prometheus query"""
        detections = []
        for result in data.get('data', {}).get('result', []):
            metric = result['metric']
            values = result['values']
            alert_name = metric.get('alertname', 'unknown')


            ############### IGNORE PrometheusTargetMissing ################
            ############### AND PrometheusJobMissing ######################
            ############### AND PrometheusAlertmanagerJobMissing ##########
            ################ AND PrometheusAlertmanagerE2eDeadManSwitch #####
            if alert_name in ["PrometheusTargetMissing", "PrometheusJobMissing", "PrometheusAlertmanagerJobMissing", "PrometheusAlertmanagerE2eDeadManSwitch"]:
                continue
            ###################################################################
            
            alert_state = metric.get('alertstate', '')
            
            self.logger.debug(f"Processing alert series: {alert_name}")
            self.logger.debug(f"Found {len(values)} data points")
            
            for timestamp, value in values:
                event_time = datetime.fromtimestamp(timestamp)
                ###########################################
                ###########################################
                ###########################################
                ################ SUBTRACTING 1 HOUR #######
                ###########################################
                #event_time = event_time - timedelta(hours=1)
                ###########################################
                ###########################################
                ###########################################
                if (float(value) > 0 and 
                    alert_state == "firing" and
                    start_time <= event_time <= end_time):
                    self.logger.debug(
                        f"Alert firing: {alert_name} at {event_time} "
                        f"[severity: {metric.get('severity', 'none')}]"
                    )
                    detections.append(DetectionEvent(
                        alert_name=alert_name,
                        firing_time=event_time,
                        severity=metric.get('severity', 'none'),
                        labels=metric
                    ))
        
        self.logger.debug(f"Total firing alerts found: {len(detections)}")
        return detections

    def _get_from_prometheus(self, start_time: datetime, end_time: datetime) -> List[DetectionEvent]:
        """Get detections from live Prometheus"""
        try:
            # Always query last 24 hours
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            self.logger.debug(f"Querying Prometheus at {self.source}")
            self.logger.debug(f"Time range: {start_time} to {end_time}")
            
            params = {
                'query': 'ALERTS',
                'start': start_time.timestamp(),
                'end': end_time.timestamp(),
                'step': '15s'
            }
            
            response = requests.get(
                f"{self.source}/api/v1/query_range",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"Found {len(data.get('data', {}).get('result', []))} alert series")
            return self._process_alert_results(data, start_time, end_time)
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch alerts from Prometheus: {e}")
            return []
    
    def _get_from_file(self, start_time: datetime, end_time: datetime) -> List[DetectionEvent]:
        """Get detections from a JSON file"""
        try:
            self.logger.debug(f"Reading alert data from file: {self.source}")
            with open(self.source, 'r') as f:
                data = json.load(f)
            
            # Use the same 24h window for consistency
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            self.logger.debug(f"Found {len(data.get('data', {}).get('result', []))} alert series")
            return self._process_alert_results(data, start_time, end_time)
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"Failed to read alerts from file: {e}")
            return []
    
    def get_detections(self, start_time: datetime, end_time: datetime) -> List[DetectionEvent]:
        """Get detections from either file or live Prometheus"""
        if self.is_file:
            return self._get_from_file(start_time, end_time)
        return self._get_from_prometheus(start_time, end_time)

class FaultDetectionBenchmark:
    """Benchmarks fault detection mechanisms"""
    
    def __init__(self, detection_mechanism: FaultDetectionMechanism):
        self.detection_mechanism = detection_mechanism
    
    def load_injected_faults(self, report_file: str) -> List[InjectedFault]:
        """Load injected faults from experiment report"""
        with open(report_file, 'r') as f:
            report = yaml.safe_load(f)
        
        # Get the first (and usually only) run
        run_id = next(iter(report['report']['runs']))
        run_data = report['report']['runs'][run_id]
        
        # Track unique treatments to avoid duplicates
        seen_treatments = set()
        faults = []
        
        for interaction in run_data['interactions'].values():
            treatment_name = interaction['treatment_name']
            
            # Skip if we've already processed this treatment
            if treatment_name in seen_treatments:
                continue
            
            seen_treatments.add(treatment_name)
            
            # Get timestamps - (datetime objects)
            start_time = interaction['treatment_start']
            end_time = interaction['treatment_end']
            
            fault = InjectedFault(
                name=treatment_name,
                start_time=start_time,
                end_time=end_time,
                type=interaction['treatment_type'],
                params={}  # TODO
            )
            
            logger.info(
                f"Loaded fault: {treatment_name} "
                f"({start_time} to {end_time})"
            )
            
            faults.append(fault)
        
        return faults
    
    def analyze_detection(self, fault: InjectedFault, detections: List[DetectionEvent]) -> Dict:
        """Analyze if and when a fault was detected"""
        relevant_detections = [
            d for d in detections 
            if fault.start_time <= d.firing_time <= fault.end_time + timedelta(minutes=1)
        ]
        
        if not relevant_detections:
            return {
                'fault_name': fault.name,
                'detected': False,
                'detection_time': None,
                'detection_latency': None,
                'alerts_triggered': []
            }
        
        first_detection = min(relevant_detections, key=lambda d: d.firing_time)
        detection_latency = (first_detection.firing_time - fault.start_time).total_seconds()
        
        return {
            'fault_name': fault.name,
            'detected': True,
            'detection_time': first_detection.firing_time,
            'detection_latency': detection_latency,
            'alerts_triggered': [
                {
                    'name': d.alert_name,
                    'time': d.firing_time,
                    'severity': d.severity,
                    'labels': d.labels
                } for d in relevant_detections
            ]
        }
    
    def benchmark(self, report_file: str) -> List[Dict]:
        """Run the benchmark using experiment report"""
        injected_faults = self.load_injected_faults(report_file)
        
        if not injected_faults:
            module_logger.warning("No faults found in experiment report")
            return []
        
        # Use current time and last 24h instead of report times
        #end_time = datetime.now()
        end_time = datetime(2024, 12, 3, 17, 48, 43, 817407)
        start_time = end_time - timedelta(hours=24)
        
        module_logger.debug(f"Analyzing time window: {start_time} to {end_time}")
        detections = self.detection_mechanism.get_detections(start_time, end_time)
        
        results = []
        for fault in injected_faults:
            result = self.analyze_detection(fault, detections)
            results.append(result)
            
            if result['detected']:
                module_logger.info(
                    f"Fault '{fault.name}' was detected after "
                    f"{result['detection_latency']:.2f} seconds"
                )
                module_logger.debug(
                    f"Triggered alerts: {', '.join(a['name'] for a in result['alerts_triggered'])}"
                )
            else:
                module_logger.info(f"Fault '{fault.name}' was not detected")
        
        return results
    
    def print_detection_summary(self, results: List[Dict]) -> None:
        """Print detailed detection summary"""
        print("\nFault Detection Analysis")
        print("=" * 100)
        
        for result in results:
            fault_name = result['fault_name']
            if result['detected']:
                print(f"\n🔴 Fault: {fault_name}")
                print(f"  Detection Latency: {result['detection_latency']:.2f} seconds")
                print("\n  Alerts Triggered:")
                
                # Group alerts by name for counting
                alert_groups = defaultdict(list)
                for alert in result['alerts_triggered']:
                    key = (alert['name'], alert['severity'])
                    alert_groups[key].append(alert)
                
                # Find alert with lowest detection time
                earliest_alert = min(result['alerts_triggered'], key=lambda x: x['time'])
                earliest_time = earliest_alert['time']
                
                # Print each unique alert with count and details
                for (alert_name, severity), alerts in alert_groups.items():
                    time_str = alerts[0]['time'].strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Use green color if this is the earliest alert
                    if alerts[0]['time'] == earliest_time:
                        print(f"\033[92m    • {alert_name} [{severity}] (×{len(alerts)})\033[0m")
                        print(f"\033[92m      First Detection: {time_str}\033[0m")
                    else:
                        print(f"    • {alert_name} [{severity}] (×{len(alerts)})")
                        print(f"      First Detection: {time_str}")
                    
                    # Print service/job info if available
                    job = alerts[0]['labels'].get('job', 'N/A')
                    rpc_service = alerts[0]['labels'].get('rpc_service', '')
                    rpc_method = alerts[0]['labels'].get('rpc_method', '')
                    
                    if job != 'N/A':
                        print(f"      Service: {job}")
                    if rpc_service and rpc_method:
                        print(f"      RPC: {rpc_service}.{rpc_method}")
            else:
                print(f"\n❌ Fault: {fault_name}")
                print("  No alerts detected")
        
        print("\n" + "=" * 100)
        
        # Add summary section
        print("\nQuick Summary:")
        print("=" * 50)
        for result in results:
            status = "✅" if result['detected'] else "❌"
            latency = f"{result['detection_latency']:.2f}s" if result['detected'] else "N/A"
            print(f"{status} {result['fault_name']}: {latency}")
        print("=" * 50)

def configure_logging(level: str):
    """Configure logging level"""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    logger.setLevel(numeric_level)
    module_logger.setLevel(numeric_level)





############ EXAMPLE USAGE #####################
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Benchmark fault detection')
    parser.add_argument('experiment_file', help='Path to experiment YAML file')
    parser.add_argument('--prometheus-data', help='Path to Prometheus data JSON file (optional)')
    parser.add_argument('--log-level', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       default='INFO',
                       help='Set the logging level')
    args = parser.parse_args()
    
    configure_logging(args.log_level)
    module_logger.debug("Logging configured") 
    
    # Initialize with either file or live Prometheus
    source = args.prometheus_data if args.prometheus_data else "http://localhost:9090"
    prometheus = PrometheusFaultDetection(source)
    benchmark = FaultDetectionBenchmark(prometheus)
    
    module_logger.debug(f"Starting benchmark with source: {source}")
    results = benchmark.benchmark(args.experiment_file)
    
    # Print summary
    benchmark.print_detection_summary(results)