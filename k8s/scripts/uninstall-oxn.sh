#!/bin/bash

# Uninstall OpenTelemetry Demo
echo "Uninstalling OpenTelemetry Demo..."
helm uninstall astronomy-shop --namespace system-under-evaluation
kubectl delete namespace system-under-evaluation --ignore-not-found

# Uninstall Kepler
echo "Uninstalling Kepler..."
helm uninstall kepler --namespace oxn-external-monitoring
kubectl delete namespace oxn-external-monitoring --ignore-not-found

# Uninstall Prometheus Stack
echo "Uninstalling Prometheus Stack..."
helm uninstall kube-prometheus --namespace oxn-external-monitoring

# Uninstall OpenEBS
echo "Uninstalling OpenEBS..."
kubectl delete -f https://openebs.github.io/charts/openebs-operator.yaml --ignore-not-found

# Uninstall OXN Platform
echo "Uninstalling OXN Platform..."
helm uninstall oxn-platform --namespace oxn
kubectl delete namespace oxn --ignore-not-found

# Clean up Helm repos
echo "Removing Helm repositories..."
helm repo remove prometheus-community
helm repo remove kepler
helm repo remove open-telemetry

echo "Uninstall complete!" 