## Set Up

Before we begin, ensure you have the following installed:

1. **Minikube**: A tool to run Kubernetes locally.
3. **Helm**: A package manager for Kubernetes.

### Step 1: Start Minikube

Start Minikube with enough resources to ensure Prometheus and your applications can run comfortably. For example:

```bash
minikube start
```

### Step 2: Install Prometheus using Helm

We use Helm to simplify the installation.

1. **Add Helm repository**:
   ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm repo update
   ```

2. **Install Prometheus**:
   ```bash
   helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring
   ```
   This installs Prometheus and related components into the `monitoring` namespace. The `kube-prometheus-stack` chart includes Prometheus server, Grafana, and other monitoring tools.

### Step 3: Adding Pod monitoring to the stack
```bash
helm upgrade prometheus prometheus-community/kube-prometheus-stack -f deployments/prometheus.yaml -n monitoring
```

### Step 4: Verify Prometheus Installation

1. Go to the kubernetes dashboard 
2. Go to the monitoring namespace
3. Check if prometheus is deployed

### Step 5: Accessing Prometheus UI

To access the Prometheus UI:

1. **Port Forwarding**:
   ```bash
   kubectl port-forward service/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring
   ```
   Note: In case the Prometheus service name is different for you Replace `service/prometheus-kube-prometheus-prometheus` with the actual Prometheus service name.

2. **Access UI**: Open http://localhost:9090 in your web browser to access the Prometheus UI.

### Step 6: Visualizing Metrics in Grafana

1. **Port Forwarding**:
   ```bash
   kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
   ```
2. **Access UI**: Open http://localhost:3000 and login with credentials 
3. default username=`admin` and password=`prom-operator`

### Step 7: setting up dashboard
You can change the namespace and add other filters if required.
1. Memory usage query:<br> 
   ```bash 
   sum(container_memory_usage_bytes{namespace="default"}) by (namespace, pod)
   ```
2. CPU usage query:<br> 
   ```bash 
   sum(rate(container_cpu_usage_seconds_total{namespace="default"}[1m])) by (namespace, pod)
   ```
3. Average request latency:
   ```bash
   sum(rate(request_latency_seconds_sum{endpoint="/predict"}[5m])) 
   / 
   sum(rate(request_latency_seconds_count{endpoint="/predict"}[5m]))
   ``` 