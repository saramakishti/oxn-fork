#!/bin/bash

# Enable required APIs
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable storage.googleapis.com

apt-get update
apt-get install -y zip