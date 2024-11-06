#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OXN_SOURCE_DIR="${SCRIPT_DIR}/../.."
CONTROL_PLANE_NODE=$(kubectl get nodes --selector=node-role.kubernetes.io/control-plane -o jsonpath='{.items[0].metadata.name}')

echo "Updating OXN source code on control plane node..."

# Create temp directory and set permissions
gcloud compute ssh "${CONTROL_PLANE_NODE}" --command='
    sudo rm -rf /tmp/oxn-source
    sudo mkdir -p /tmp/oxn-source
    sudo chown -R $(whoami):$(whoami) /tmp/oxn-source
    sudo chmod -R 755 /tmp/oxn-source
'

# Copy updated source files
gcloud compute scp --recurse "${OXN_SOURCE_DIR}"/* "${CONTROL_PLANE_NODE}:/tmp/oxn-source/"

# Update installation
gcloud compute ssh "${CONTROL_PLANE_NODE}" --command='
    sudo rm -rf /opt/oxn/*
    sudo mv /tmp/oxn-source/* /opt/oxn/
    sudo rm -r /tmp/oxn-source
    sudo chown -R $(whoami):$(whoami) /opt/oxn
    
    cd /opt/oxn
    pip install  .

    # Verify installation
    oxn --help
'

echo "OXN source code updated successfully!"