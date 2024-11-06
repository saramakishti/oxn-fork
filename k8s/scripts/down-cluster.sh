#!/bin/bash

set -e

CLUSTER_NAME="oxn.dev.com"

# Set environment variable for kOps state store
export KOPS_STATE_STORE="gs://$(terraform output -raw kops_state_store_bucket_name)"

# Delete the cluster using kOps
kops delete cluster --name "${CLUSTER_NAME}" --yes

# Terraform destroy to remove GCS bucket
terraform destroy -auto-approve

# Remove kubeconfig file
rm -f "${CLUSTER_NAME}.config"