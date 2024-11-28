# Prometheus Tools

Scripts for working with Prometheus alerts and metrics in the OpenTelemetry Demo.

## Scripts

- `fault_detection_benchmark.py`: Analyze if injected faults were detected by Prometheus alerts
- `visualize_alerts.py`: Display Prometheus alert history
- `check_metrics.py`: Monitor key metrics in real-time
- `config_prometheus.py`: Update Prometheus alert rules via helm

## Usage

```bash
# Analyze fault detection from a saved Prometheus response
python3 fault_detection_benchmark.py path/to/experiment/report.yaml --prometheus-data alerts.json

# View alert history
python3 visualize_alerts.py --hours 24 --download

# Monitor metrics
python3 check_metrics.py

# Update alert rules
python3 config_prometheus.py update-rules --latency-threshold 300
``` 