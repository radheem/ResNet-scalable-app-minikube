## Setup Environment
```bash
python3 scripts/load_model.py
```
```bash
eval $(minikube docker-env)
```
``` bash
docker buildx build -t flask-app:latest -f ./docker/producer/Dockerfile.flaskapp .
```
``` bash
docker buildx build -t worker-app:latest -f ./docker/consumer/Dockerfile.worker .
```
``` bash
docker build -t autoscaler:latest . -f Dockerfile.CPA 
```
``` bash
minikube start --driver=docker
```
NOTE: You may specify the number of cpu cores and memory you want to allocate to minikube using --cpus \<number of cpu cores> --memory \<memory in MBs>

## Setting Up Prometheus
Before we begin, make sure you have [Helm](https://helm.sh/docs/intro/install/) intalled

### Install Prometheus using Helm

We use Helm to simplify the installation.
1. **Adding CRDs**
    ``` bash
    chmod +x scripts/apply-prometheus-crds.sh
    ```
    ``` bash
    ./scripts/apply-prometheus-crds.sh
    ```
2. **Add Helm repository**:
   ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   ```
   ```bash
   helm repo update
   ```
3. **Create Monitoring namespace**
    ```bash
    kubectl apply -f ./deployments/monitoring-namespace.yaml
    ```
    
4. **Install Prometheus**:
   ```bash
   helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring
   ```
   This installs Prometheus and related components into the `monitoring` namespace. The `kube-prometheus-stack` chart includes Prometheus server, Grafana, and other monitoring tools.

### Adding Pod monitoring to the stack
```bash
helm upgrade prometheus prometheus-community/kube-prometheus-stack -f deployments/prometheus.yaml -n monitoring
```

### Verify Prometheus Installation

1. Go to the kubernetes dashboard 
2. Go to the monitoring namespace
3. Check if prometheus is deployed

### Accessing Prometheus UI

1. **Port Forwarding**:
   ```bash
   kubectl port-forward service/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring
   ```
   Note: In case the Prometheus service name is different for you Replace `service/prometheus-kube-prometheus-prometheus` with the actual Prometheus service name.

2. **Access UI**: Open http://localhost:9090 in your web browser to access the Prometheus UI.

### Visualizing Metrics in Grafana

1. **Port Forwarding**:
   ```bash
   kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
   ```
2. **Access UI**: Open http://localhost:3000 and login with credentials 

3. Default username=`admin` and password=`prom-operator`

### setting up dashboard
You can change the namespace and add other filters if required.
1. Memory usage query:
   ```bash 
   sum(container_memory_usage_bytes{namespace="default"}) by (namespace, pod)
   ```
2. CPU usage query: 
   ```bash 
   sum(rate(container_cpu_usage_seconds_total{namespace="default"}[1m])) by (namespace, pod)
   ```
3. Average request latency:
   ```bash
   sum(rate(request_latency_seconds_sum{endpoint="/predict"}[5m])) 
   / 
   sum(rate(request_latency_seconds_count{endpoint="/predict"}[5m]))
   ``` 
## Deploying the flask app
``` bash
kubectl apply -f deployments/app.yaml
``` 
## Deploying custom Autoscaler
Make sure flask app hpa is not active
```bash
kubectl delete hpa flask-app-hpa
```
```bash
kubectl apply -f ./deployments/autoscaler.yaml
```

## Access the deployment 
```bash 
minikube tunnel
```

## Verify deployment
1. Go to any browser 
2. Visit http://localhost:5000

## Access minikube dashboard using
```bash 
minikube dashboard
```
## Notes 
- The match label is flask-app