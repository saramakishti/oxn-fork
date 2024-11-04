#!/bin/bash
set -e

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "kubectl is not installed"
    exit 1
fi

# Check if helm is available
if ! command -v helm &> /dev/null; then
    echo "helm is not installed"
    exit 1
fi

# Define directories relative to script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MANIFESTS_DIR="${SCRIPT_DIR}/../manifests"
DASHBOARDS_DIR="${SCRIPT_DIR}/../dashboards"

# Verify directories exist
if [ ! -d "$MANIFESTS_DIR" ]; then
    echo "Error: Manifests directory not found: $MANIFESTS_DIR"
    exit 1
fi

if [ ! -d "$DASHBOARDS_DIR" ]; then
    echo "Error: Dashboards directory not found: $DASHBOARDS_DIR"
    exit 1
fi

echo "Installing OpenEBS..."
kubectl apply -f https://openebs.github.io/charts/openebs-operator.yaml

echo "Installing Prometheus Stack..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install kube-prometheus prometheus-community/kube-prometheus-stack \
    --namespace oxn-external-monitoring \
    --create-namespace \
    --version 62.5.1 \
    -f "${MANIFESTS_DIR}/values_kube_prometheus.yaml"

echo "Installing Kepler..."
helm repo add kepler https://sustainable-computing-io.github.io/kepler-helm-chart
helm repo update
helm install kepler kepler/kepler \
    --namespace oxn-external-monitoring \
    --create-namespace \
    --set serviceMonitor.enabled=true \
    --set serviceMonitor.labels.release=kube-prometheus \
    -f "${MANIFESTS_DIR}/values_kepler.yaml"

echo "Waiting for Grafana pod to be ready..."
kubectl wait --for=condition=ready pod \
    -l app.kubernetes.io/name=grafana \
    -n oxn-external-monitoring \
    --timeout=300s

echo "Copying Kepler dashboard to Grafana..."
GF_POD=$(kubectl get pod \
    -n oxn-external-monitoring \
    -l app.kubernetes.io/name=grafana \
    -o jsonpath="{.items[0].metadata.name}")
kubectl cp "${DASHBOARDS_DIR}/kepler_dashboard.json" \
    "oxn-external-monitoring/${GF_POD}:/tmp/dashboards/kepler_dashboard.json"

echo "Installing OpenTelemetry Demo..."
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update
helm install astronomy-shop open-telemetry/opentelemetry-demo \
    --namespace system-under-evaluation \
    --create-namespace \
    -f "${MANIFESTS_DIR}/values_opentelemetry_demo.yaml"

echo "Installation complete!"

    