# Kubernetes Cluster Management Scripts

These scripts manage a Kubernetes cluster and install the OpenTelemetry Demo.

## Prerequisites

- Google Cloud SDK
- Terraform 
- kubectl
- kOps 
- Helm >= 3.0
- GCP Project

## Scripts Overview

### Cluster Management
- `setup.sh`: Enables required GCP APIs for the project
- `up-cluster.sh <project-id>`: Creates GKE cluster with spot instances for cost optimization
- `down-cluster.sh`: Deletes the cluster and cleans up resources including the kOps state store

### OXN Installation and Management
- `install-oxn.sh`: Sets up the complete environment:
  - Installs OpenEBS for storage
  - Deploys Prometheus Stack for monitoring
  - Installs Kepler for energy metrics
  - Deploys OpenTelemetry Demo as the system under test
  - Installs OXN on the control plane node

  Note: be patient, this takes a while (5+ minutes)
- `uninstall-oxn.sh`: Removes all installed components from the cluster
- `update-oxn.sh`: Updates the OXN installation on the control plane node with new source code

### Experiment Management
- `run-experiment.sh <experiment-yaml-file> [additional oxn arguments]`: 
  - Copies experiment configuration to the control plane
  - Executes the experiment using OXN
  - Example: `./run-experiment.sh my-experiment.yaml --logfile test.log --loglevel info`

- `extract-results.sh <remote-results-path> <local-destination-dir>`:
  - Copies experiment results from the control plane to your local machine
  - Example: `./extract-results.sh /opt/oxn/results ./local-results`

## Typical Workflow

1. Enable GCP APIs:
   ```bash
   ./setup.sh
   ```

2. Create the cluster:
   ```bash
   ./up-cluster.sh your-project-id
   ```

3. Install OXN and dependencies:
   ```bash
   ./install-oxn.sh
   ```

4. Run experiments:
   ```bash
   ./run-experiment.sh path/to/experiment.yaml
   ```

5. Extract results:
   ```bash
   ./extract-results.sh /opt/oxn/results ./my-results
   ```

6. When finished, clean up:
   ```bash
   ./uninstall-oxn.sh
   ./down-cluster.sh
   ```