#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_DIR="${SCRIPT_DIR}/../config"

# Function to generate a random alphabetic prefix
generate_random_prefix() {
    LC_ALL=C tr -dc 'a-z' < /dev/urandom | fold -w 6 | head -n 1
}

# Generate the cluster name only if the file does not exist
CLUSTER_NAME_FILE="${CONFIG_DIR}/.cluster-name"
if [ ! -f "$CLUSTER_NAME_FILE" ]; then
    mkdir -p "${CONFIG_DIR}"
    PREFIX=$(generate_random_prefix)
    CLUSTER_NAME="${PREFIX}.oxn.dev.com"
    echo "$CLUSTER_NAME" > "$CLUSTER_NAME_FILE"
else
    # Read the stored cluster name
    CLUSTER_NAME=$(cat "$CLUSTER_NAME_FILE")
fi

# Export the cluster name for use in other scripts
export CLUSTER_NAME
