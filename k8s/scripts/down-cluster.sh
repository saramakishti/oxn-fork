#!/bin/bash

set -e


if [ -z "$1" ]; then
    echo "Error: GCP project ID missing"
    echo "Usage: $0 <project_id>"
    exit 1
fi

PROJECT_ID="$1"
CLUSTER_NAME="oxn.dev.com"

# Set environment variable for kOps state store
export KOPS_STATE_STORE="gs://$(terraform output -raw kops_state_store_bucket_name)"

# Delete the cluster using kOps
kops delete cluster --name "${CLUSTER_NAME}" --yes

# Terraform destroy to remove GCS bucket
terraform destroy -auto-approve -var="project_id=${PROJECT_ID}"

# Remove kubeconfig file
rm -f "${CLUSTER_NAME}.config"