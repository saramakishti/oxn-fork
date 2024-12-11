import argparse
import requests
from datetime import datetime, timedelta
import time
import subprocess
import sys
import signal
import logging
from typing import Dict, List, Tuple
from collections import defaultdict
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PROMETHEUS_BASE_URL = "http://localhost:9090/api/v1"

class PortForwarder:
    def __init__(self):
        self.processes = []
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)
        
    def start(self) -> bool:
        """Setup required port-forward"""
        try:
            prometheus_forward = subprocess.Popen(
                ["kubectl", "port-forward", 
                "-n", "system-under-evaluation",
                "svc/astronomy-shop-prometheus-server",
                "9090:9090"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.processes = [prometheus_forward]
            # Give port-forward time to establish
            time.sleep(1)
            logger.info("Setting up port-forward...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup port-forward: {e}")
            self.cleanup()
            return False

    def cleanup(self, *args):
        """Clean up port-forward processes"""
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

def save_prometheus_response(response_data: Dict, timestamp: str) -> None:
    """Save raw Prometheus response to a JSON file"""
    filename = f"prometheus-alerts-{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(response_data, f, indent=2)
    logger.info(f"Saved raw Prometheus response to {filename}")

def get_alert_transitions(start_time: datetime, end_time: datetime, download: bool = False) -> List[Dict]:
    """Get alert firing history with focus on state transitions"""
    try:
        params = {
            'query': 'ALERTS',
            'start': start_time.timestamp(),
            'end': end_time.timestamp(),
            'step': '15s'
        }
        logger.info(f"Querying Prometheus at {PROMETHEUS_BASE_URL}")
        logger.info(f"Time range: {start_time} to {end_time}")
        response = requests.get(
            f"{PROMETHEUS_BASE_URL}/query_range",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        response_data = response.json()
        logger.info(f"Found {len(response_data.get('data', {}).get('result', []))} alert series")
        # Save raw response if requested
        if download:
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            save_prometheus_response(response_data, timestamp)
        
        # Track alert states and transitions
        alert_states = defaultdict(lambda: {'active': False, 'transitions': []})
        
        for result in response_data.get('data', {}).get('result', []):
            metric = result['metric']
            alert_name = metric.get('alertname', 'unknown')
            severity = metric.get('severity', 'none')
            
            last_state = False
            for timestamp, value in result['values']:
                current_state = float(value) > 0
                
                # Detect state transition
                if current_state != last_state:
                    time = datetime.fromtimestamp(timestamp)
                    alert_states[alert_name]['transitions'].append({
                        'time': time,
                        'state': 'firing' if current_state else 'resolved',
                        'severity': severity
                    })
                last_state = current_state
        
        return alert_states
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch alert history: {e}")
        return {}

def display_alert_timeline(alert_states: Dict):
    """Display alert transitions in chronological order, grouped by timestamp and alert name"""
    if not alert_states:
        print("No alert data available")
        return

    # Group transitions by timestamp
    grouped_transitions = defaultdict(list)
    for alert_name, data in alert_states.items():
        for transition in data['transitions']:
            time_key = transition['time'].strftime('%Y-%m-%d %H:%M:%S')
            grouped_transitions[time_key].append({
                'alert': alert_name,
                'state': transition['state'],
                'severity': transition['severity']
            })
    
    print("\nAlert Timeline:")
    print("=" * 100)
    
    # Display grouped transitions
    for time_str in sorted(grouped_transitions.keys()):
        transitions = grouped_transitions[time_str]
        
        # Group by state and alert name
        firing = defaultdict(list)
        resolved = defaultdict(list)
        
        for t in transitions:
            if t['state'] == 'firing':
                firing[t['alert']].append(t['severity'])
            else:
                resolved[t['alert']].append(t['severity'])
        
        if firing:
            alerts = [f"{alert}[{severity[0].upper()}] (×{len(severity)})" 
                     for alert, severity in firing.items()]
            print(f"{time_str} 🔴 Firing: {', '.join(alerts)}")
            
        if resolved:
            alerts = [f"{alert} (×{len(severities)})" 
                     for alert, severities in resolved.items()]
            print(f"{time_str} ✅ Resolved: {', '.join(alerts)}")
    
    print("=" * 100)

def main():
    parser = argparse.ArgumentParser(description='Display Prometheus alert history')
    parser.add_argument('--hours', type=int, default=24,
                      help='Number of hours of history to show (default: 24)')
    parser.add_argument('--download', action='store_true',
                      help='Download raw Prometheus response to a JSON file')
    args = parser.parse_args()
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=args.hours)
    
    forwarder = PortForwarder()
    if not forwarder.start():
        sys.exit(1)
    
    try:
        logger.info("Fetching alert history...")
        alert_states = get_alert_transitions(start_time, end_time, download=args.download)
        display_alert_timeline(alert_states)
        
    finally:
        forwarder.cleanup()

if __name__ == "__main__":
    main() 