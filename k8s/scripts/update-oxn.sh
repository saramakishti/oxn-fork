#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OXN_SOURCE_DIR="${SCRIPT_DIR}/../.."
CONTROL_PLANE_NODE=$(kubectl get nodes --selector=node-role.kubernetes.io/control-plane -o jsonpath='{.items[0].metadata.name}')

echo "Updating OXN source code on control plane node..."

# Create temp zip file
echo "Creating zip archive of source code..."
rm -f /tmp/oxn-source.zip
# Exclude virtualenv and terraform files
(cd "${OXN_SOURCE_DIR}" && zip -r /tmp/oxn-source.zip ./* -x "k8s/scripts/.terraform/*" -x "venv/*")

# Copy zip file and extract on remote
echo "Copying and extracting source code..."
gcloud compute scp /tmp/oxn-source.zip "${CONTROL_PLANE_NODE}:/tmp/"

gcloud compute ssh "${CONTROL_PLANE_NODE}" --command='
    # Clean up old files but preserve virtualenv
    sudo rm -rf /opt/oxn/*
    sudo mkdir -p /opt/oxn
    sudo chown -R $(whoami):$(whoami) /opt/oxn
    
    # Extract OXN source
    cd /opt/oxn
    unzip -q /tmp/oxn-source.zip
    rm /tmp/oxn-source.zip
    
    # Create new virtualenv
    python3 -m venv venv
    source venv/bin/activate
    
    # Install OXN in virtualenv
    pip3 install .
    
    # Verify installation
    which oxn
    oxn --help
'

rm -f /tmp/oxn-source.zip

echo "OXN source code updated successfully!"