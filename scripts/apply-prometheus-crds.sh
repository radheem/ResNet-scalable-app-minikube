#!/bin/bash

# Define the URLs for the CRD files
CRD_URLS=(
  "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/master/example/prometheus-operator-crd/monitoring.coreos.com_servicemonitors.yaml"
  "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/master/example/prometheus-operator-crd/monitoring.coreos.com_prometheuses.yaml"
  "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/master/example/prometheus-operator-crd/monitoring.coreos.com_podmonitors.yaml"
  "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/master/example/prometheus-operator-crd/monitoring.coreos.com_prometheusrules.yaml"
)

# Apply each CRD
for url in "${CRD_URLS[@]}"; do
  echo "Applying $url"
  kubectl apply -f "$url"
done

echo "All CRDs applied successfully."
