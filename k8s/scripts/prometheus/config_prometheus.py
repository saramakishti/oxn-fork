import click
import subprocess
import yaml
from pathlib import Path


### NOTES #######
# astronomy-shop-rapid-http-latency-alerts minimum range is 90s . else empty
# astronomy-shop-critical-service-rpc-latency-alerts minimum range is 90s . else empty
# histogram_quantile(0.95, sum by (job, rpc_method, rpc_service, le) (rate(rpc_server_duration_milliseconds_bucket{job=~"opentelemetry-demo/(checkoutservice|adservice|productcatalogservice)",le!="infinity",rpc_grpc_status_code="0"}[90s]))) >300
# You need to port forward to the prometheus server to access it
# see README.md for command


class HelmUpgradeError(Exception):
    pass

@click.group()
def cli():
    """Manage Prometheus rules for the OpenTelemetry Demo"""
    pass

@cli.command()
@click.option('--namespace', default='system-under-evaluation', help='Kubernetes namespace')
@click.option('--latency-threshold', type=int, help='Latency threshold in ms')
@click.option('--evaluation-window', help='Evaluation window (e.g., "5m")')
@click.option('--duration', help='Duration before alerting (e.g., "2m")')
@click.option('--dry-run', is_flag=True, help='Perform a dry-run')
def update_rules(namespace, latency_threshold, evaluation_window, duration, dry_run):
    """Update Prometheus alert rules via helm upgrade"""
    
    # Build the --set arguments
    set_args = []
    
    if latency_threshold:
        set_args.append(f"prometheus.serverFiles.alerting_rules.groups[0].rules[0].expr={latency_threshold}")
    
    if evaluation_window:
        set_args.append(f"prometheus.serverFiles.alerting_rules.groups[0].rules[0].for={evaluation_window}")
    
    # Build helm command
    cmd = [
        "helm", "upgrade",
        "astronomy-shop",
        "open-telemetry/opentelemetry-demo",
        "--namespace", namespace,
        "--reuse-values"  # Preserve existing values
    ]
    
    # Add all --set arguments
    for arg in set_args:
        cmd.extend(["--set", arg])
    
    if dry_run:
        cmd.append("--dry-run")
    
    try:
        # Execute helm upgrade
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        click.echo(f"Successfully updated rules:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        raise HelmUpgradeError(f"Helm upgrade failed:\n{e.stderr}")

@cli.command()
@click.option('--namespace', default='system-under-evaluation', help='Kubernetes namespace')
def get_current_rules(namespace):
    """Get current Prometheus rules configuration"""
    cmd = [
        "helm", "get", "values",
        "astronomy-shop",
        "--namespace", namespace,
        "-o", "yaml"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        values = yaml.safe_load(result.stdout)
        # Extract and display prometheus rules
        rules = values.get('prometheus', {}).get('serverFiles', {}).get('alerting_rules', {})
        click.echo(yaml.dump(rules))
    except subprocess.CalledProcessError as e:
        raise HelmUpgradeError(f"Failed to get values:\n{e.stderr}")

if __name__ == '__main__':
    cli()