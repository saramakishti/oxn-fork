#!/bin/bash


set -e

# parameters
if [ $# -ne 1 ]; then
    echo "Usage: $0 <project-id>"
    echo "Example: $0 my-gcp-project"
    exit 1
fi

# create GCS bucket
terraform apply -auto-approve

# Configuration variables
CLUSTER_NAME="oxn.dev.com"          # If you want to change the cluster name, you need to update the  variable in down-cluster.sh and install-oxn.sh
PROJECT_ID=$1                       # GCP project ID
ZONE="europe-west1-b"               # Single zone since HA is not needed
NODE_COUNT=3
CONTROL_PLANE_SIZE="e2-standard-2"  
NODE_SIZE="e2-standard-2"           

# Get the state store bucket name from Terraform output
export KOPS_STATE_STORE="gs://$(terraform output -raw kops_state_store_bucket_name)"

# Create the cluster configuration
echo "Creating cluster configuration..."
kops create cluster \
    --name="${CLUSTER_NAME}" \
    --state="${KOPS_STATE_STORE}" \
    --zones="${ZONE}" \
    --control-plane-zones="${ZONE}" \
    --node-count="${NODE_COUNT}" \
    --control-plane-size="${CONTROL_PLANE_SIZE}" \
    --node-size="${NODE_SIZE}" \
    --control-plane-count=1 \
    --networking=cilium \
    --cloud=gce \
    --project="${PROJECT_ID}" \


# Get the instance group specs
echo "Modifying instance groups to use spot instances..."
kops get ig --name "${CLUSTER_NAME}" -o yaml > ig_specs.yaml

# Modify the instance group specs to use spot instances
# This adds the gcpProvisioningModel: SPOT to both node and control-plane specs
sed -i '/spec:/a\  gcpProvisioningModel: SPOT' ig_specs.yaml


# Apply the instance group specs
echo "Applying instance group configurations..."
kops replace -f ig_specs.yaml

# Create the cluster
echo "Creating the cluster..."
kops update cluster --name="${CLUSTER_NAME}" --yes

# Update local kubeconfig
kops export kubeconfig --admin --kubeconfig="${CLUSTER_NAME}.config"
kops export kubeconfig --admin
# Wait for the cluster to be ready
echo "Waiting for cluster to be ready..."
kops validate cluster --wait 10m

