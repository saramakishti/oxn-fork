# Kubernetes Cluster Management Scripts

These scripts manage a Kubernetes cluster and install the OpenTelemetry Demo.

## Prerequisites

- Google Cloud SDK
- Terraform 
- kubectl
- kOps 
- Helm >= 3.0
- GCP Project

## Scripts

- `setup.sh`: Enables required GCP APIs
- `up-cluster.sh <project-id>`: Creates GKE cluster with spot instances
- `install-oxn.sh`: Installs OpenEBS, Prometheus Stack, Kepler, and OpenTelemetry Demo on the cluster
- `uninstall-oxn.sh`: Removes all installed components
- `down-cluster.sh`: Deletes the cluster and cleans up resources