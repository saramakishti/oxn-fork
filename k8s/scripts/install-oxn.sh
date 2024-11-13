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
CLUSTER_NAME="oxn.dev.com" 

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

echo "Copying kubeconfig and OXN source to control plane node..."
CONTROL_PLANE_NODE=$(kubectl get nodes --selector=node-role.kubernetes.io/control-plane -o jsonpath='{.items[0].metadata.name}')
OXN_SOURCE_DIR="${SCRIPT_DIR}/../.."

# Create directories on control plane node and set permissions
gcloud compute ssh "${CONTROL_PLANE_NODE}" --command='
    sudo mkdir -p /opt/oxn ~/.kube
    sudo mkdir -p /tmp/oxn-source
    sudo chown -R $(whoami):$(whoami) /tmp/oxn-source
    sudo chmod -R 755 /tmp/oxn-source
'

# Copy kubeconfig
gcloud compute scp "${CLUSTER_NAME}.config" "${CONTROL_PLANE_NODE}:/tmp/kubeconfig"
gcloud compute ssh "${CONTROL_PLANE_NODE}" --command="sudo mv /tmp/kubeconfig ~/.kube/config"

# Copy OXN source files
gcloud compute scp --recurse "${OXN_SOURCE_DIR}"/* "${CONTROL_PLANE_NODE}:/tmp/oxn-source/"
gcloud compute ssh "${CONTROL_PLANE_NODE}" --command='
    sudo apt install -y unzip
    sudo mv /tmp/oxn-source/* /opt/oxn/
    sudo rm -r /tmp/oxn-source
    sudo chown -R $(whoami):$(whoami) /opt/oxn
'
echo "installing OXN..."

# Install Python and pip
gcloud compute ssh "${CONTROL_PLANE_NODE}" --command='
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
'

# Install OXN
gcloud compute ssh "${CONTROL_PLANE_NODE}" --command='
    cd /opt/oxn
    # not the best solution
    sudo pip3 install .
    
    # verify installation
    export PATH="$PATH:$HOME/.local/bin:/usr/local/bin"
    which oxn
    oxn --help
'


echo "Installation complete!"
echo "To run an experiment: ./run-experiment.sh <experiment-yaml-file> [additional oxn arguments]"
echo "To extract results: ./extract-results.sh <remote-results-path> <local-destination-dir>"
    