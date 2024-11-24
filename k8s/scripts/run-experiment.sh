#!/bin/bash
if [ $# -lt 1 ]; then
    echo "Usage: $0 <experiment-yaml-file> [additional oxn arguments]"
    echo "Example: $0 my-experiment.yaml --times 3 --report report.yaml"
    exit 1
fi

EXPERIMENT_FILE="$1"
shift  # Remove first argument, leaving remaining args for oxn

# Copy experiment file to control plane
CONTROL_PLANE_NODE=$(kubectl get nodes --selector=node-role.kubernetes.io/control-plane -o jsonpath='{.items[0].metadata.name}')

REMOTE_PATH="/tmp/$(basename ${EXPERIMENT_FILE})"
gcloud compute scp "${EXPERIMENT_FILE}" "${CONTROL_PLANE_NODE}:${REMOTE_PATH}"

# Run experiment with virtualenv activated
gcloud compute ssh "${CONTROL_PLANE_NODE}" --command="cd /opt/oxn && source venv/bin/activate && oxn ${REMOTE_PATH} $*"