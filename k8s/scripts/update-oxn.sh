#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OXN_SOURCE_DIR="${SCRIPT_DIR}/../.."
CONTROL_PLANE_NODE=$(kubectl get nodes --selector=node-role.kubernetes.io/control-plane -o jsonpath='{.items[0].metadata.name}')

echo "Updating OXN source code on control plane node..."

# Create temp zip file
echo "Creating zip archive of source code..."
rm -f /tmp/oxn-source.zip
cd "${OXN_SOURCE_DIR}" && zip -r /tmp/oxn-source.zip ./*

# Copy zip file and extract on remote
echo "Copying and extracting source code..."
gcloud compute scp /tmp/oxn-source.zip "${CONTROL_PLANE_NODE}:/tmp/"

gcloud compute ssh "${CONTROL_PLANE_NODE}" --command='
    sudo pip3 uninstall -y oxn
    # Clean and prepare directories
    sudo rm -rf /tmp/oxn-source /opt/oxn/*
    sudo mkdir -p /tmp/oxn-source
    sudo chown -R $(whoami):$(whoami) /tmp/oxn-source
    
    # Extract zip file
    cd /tmp/oxn-source
    unzip -q /tmp/oxn-source.zip
    rm /tmp/oxn-source.zip
    
    # Move files to installation directory
    sudo mv ./* /opt/oxn/
    sudo rm -r /tmp/oxn-source
    sudo chown -R $(whoami):$(whoami) /opt/oxn
    
    cd /opt/oxn
    # not the best solution
    sudo pip3 install .
    
    # verify installation
    export PATH="$PATH:$HOME/.local/bin:/usr/local/bin"
    oxn --help
'

# Cleanup local temp file
rm -f /tmp/oxn-source.zip

echo "OXN source code updated successfully!"