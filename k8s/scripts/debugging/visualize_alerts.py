import argparse
import requests
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
import subprocess
import sys
import signal
import logging
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PROMETHEUS_BASE_URL = "http://localhost:9090/api/v1"
SEVERITY_COLORS = {
    'critical': 'red',
    'warning': 'orange',
    'info': 'blue',
    'none': 'gray'
}

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

def get_alert_rules() -> List[Dict]:
    """Get all configured alert rules from Prometheus"""
    try:
        response = requests.get(f"{PROMETHEUS_BASE_URL}/rules", timeout=10)
        response.raise_for_status()
        
        rules_data = response.json()
        alert_rules = []
        
        for group in rules_data.get('data', {}).get('groups', []):
            for rule in group.get('rules', []):
                if rule.get('type') == 'alerting':
                    alert_rules.append({
                        'name': rule.get('name'),
                        'severity': rule.get('labels', {}).get('severity', 'none')
                    })
        
        return alert_rules
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch alert rules: {e}")
        return []

def get_alert_history(start_time: datetime, end_time: datetime) -> pd.DataFrame:
    """Get alert firing history from Prometheus"""
    try:
        params = {
            'query': 'ALERTS',
            'start': start_time.timestamp(),
            'end': end_time.timestamp(),
            'step': '1m'  # 1 minute resolution
        }
        
        response = requests.get(
            f"{PROMETHEUS_BASE_URL}/query_range",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        # Convert response to DataFrame
        data = response.json()
        alert_data = []
        
        for result in data.get('data', {}).get('result', []):
            metric = result['metric']
            values = result['values']
            
            for timestamp, value in values:
                if float(value) > 0:  # Alert is firing
                    alert_data.append({
                        'timestamp': pd.to_datetime(timestamp, unit='s'),
                        'alertname': metric.get('alertname'),
                        'severity': metric.get('severity', 'none')
                    })
        
        return pd.DataFrame(alert_data)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch alert history: {e}")
        return pd.DataFrame()

def create_timeline(
    alert_data: pd.DataFrame,
    start_time: datetime,
    end_time: datetime,
    output_file: str = None
):
    """Create timeline visualization of alerts"""
    if alert_data.empty:
        logger.error("No alert data to visualize")
        return
    
    # Setup the plot
    plt.figure(figsize=(15, 8))
    
    # Get unique alert names
    alert_names = alert_data['alertname'].unique()
    
    # Create timeline bars for each alert
    for idx, alert_name in enumerate(alert_names):
        alert_instances = alert_data[alert_data['alertname'] == alert_name]
        
        for _, instance in alert_instances.iterrows():
            severity = instance['severity']
            color = SEVERITY_COLORS.get(severity, 'gray')
            
            plt.hlines(
                y=idx,
                xmin=instance['timestamp'],
                xmax=instance['timestamp'] + pd.Timedelta(minutes=1),
                color=color,
                linewidth=10
            )
    
    # Customize the plot
    plt.yticks(range(len(alert_names)), alert_names)
    plt.xlabel('Time')
    plt.ylabel('Alert Name')
    plt.title('Alert Timeline')
    plt.grid(True, axis='x', alpha=0.3)
    
    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], color=color, label=severity, linewidth=4)
        for severity, color in SEVERITY_COLORS.items()
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save or display
    if output_file:
        plt.savefig(output_file)
        logger.info(f"Saved visualization to {output_file}")
    else:
        plt.show()

def main():
    parser = argparse.ArgumentParser(description='Visualize Prometheus alert history')
    parser.add_argument('--hours', type=int, default=24,
                      help='Number of hours of history to show (default: 24)')
    parser.add_argument('--output', type=str,
                      help='Output file path (default: display plot)')
    args = parser.parse_args()
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=args.hours)
    
    # Setup port-forward
    forwarder = PortForwarder()
    if not forwarder.start():
        sys.exit(1)
    
    try:
        # Get alert rules and history
        logger.info("Fetching alert rules...")
        alert_rules = get_alert_rules()
        
        logger.info("Fetching alert history...")
        alert_data = get_alert_history(start_time, end_time)
        
        # Create visualization
        logger.info("Creating visualization...")
        create_timeline(alert_data, start_time, end_time, args.output)
        
    finally:
        logger.info("Cleaning up port-forward...")
        forwarder.cleanup()

if __name__ == "__main__":
    main() 