# Scalable Object Identification App

This repository demonstrates a scalable object identification application, emphasizing scalability and monitoring. The application is containerized using Docker and deployed on a local Kubernetes cluster via Minikube. Monitoring is integrated using Prometheus, and a load testing script is provided to evaluate performance under varying workloads.

## Features

- **Scalability:** Designed to efficiently handle increasing workloads within a Kubernetes environment.

- **Containerization:** Utilizes Docker for consistent and portable deployment across different environments.

- **Kubernetes Deployment:** Deployed on Minikube, facilitating local development and testing of Kubernetes applications.

- **Monitoring:** Integrated with Prometheus to collect and visualize performance metrics, aiding in proactive system management.

- **Load Testing:** Includes scripts to simulate various load scenarios, enabling performance evaluation and optimization.

## Prerequisites

Before setting up the environment, ensure you have the following installed:

- [Python 3](https://www.python.org/downloads/)

- [Docker](https://docs.docker.com/get-docker/)

- [Minikube](https://minikube.sigs.k8s.io/docs/start/)

- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)

- [Helm](https://helm.sh/docs/intro/install/)

## Setup Environment

1. **Load the Model:**

   ```bash
   python3 scripts/load_model.py
   ```


2. **Configure Docker to Use Minikube's Environment:**

   ```bash
   eval $(minikube docker-env)
   ```


3. **Build Docker Images:**

   - Flask Application:

     ```bash
     docker buildx build -t flask-app:latest -f ./docker/producer/Dockerfile.flaskapp .
     ```

   - Worker Application:

     ```bash
     docker buildx build -t worker-app:latest -f ./docker/consumer/Dockerfile.worker .
     ```

   - Custom Autoscaler:

     ```bash
     docker buildx build -t autoscaler:latest . -f Dockerfile.CPA
     ```

4. **Start Minikube:**

   ```bash
   minikube start --driver=docker
   ```


   *Note:* You can specify the number of CPU cores and memory for Minikube using the `--cpus` and `--memory` flags. For example:

   ```bash
   minikube start --driver=docker --cpus 4 --memory 8192
   ```


## Setting Up Prometheus

Prometheus is used for monitoring the application's performance metrics.

1. **Install Prometheus Using Helm:**

   - **Add Helm Repository:**

     ```bash
     helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
     helm repo update
     ```

   - **Create Monitoring Namespace:**

     ```bash
     kubectl apply -f ./deployments/monitoring-namespace.yaml
     ```

   - **Install Prometheus:**

     ```bash
     helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring
     ```

     This command installs Prometheus and related components into the `monitoring` namespace.

2. **Apply Prometheus Custom Resource Definitions (CRDs):**

   ```bash
   chmod +x scripts/apply-prometheus-crds.sh
   ./scripts/apply-prometheus-crds.sh
   ```


3. **Upgrade Prometheus with Custom Configuration:**

   ```bash
   helm upgrade prometheus prometheus-community/kube-prometheus-stack -f deployments/prometheus.yaml -n monitoring
   ```


## Deploying the Flask Application

Deploy the Flask application using the provided Kubernetes manifests:


```bash
kubectl apply -f deployments/app.yaml
```


## Deploying the Custom Autoscaler

1. **Ensure the Default Horizontal Pod Autoscaler (HPA) Is Not Active:**

   ```bash
   kubectl delete hpa flask-app-hpa
   ```


2. **Deploy the Custom Autoscaler:**

   ```bash
   kubectl apply -f ./deployments/autoscaler.yaml
   ```


## Accessing the Deployment

To access the deployed application:

1. **Start Minikube Tunnel:**

   ```bash
   minikube tunnel
   ```


2. **Verify Deployment:**

   - Open a web browser and navigate to [http://localhost:5000](http://localhost:5000) to access the application.

## Monitoring and Visualization

- **Access Minikube Dashboard:**

  
```bash
  minikube dashboard
  ```


  This command opens the Kubernetes dashboard, providing an overview of the cluster's resources and deployments.

- **Access Prometheus UI:**

  
```bash
  kubectl port-forward service/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring
  ```


  Navigate to [http://localhost:9090](http://localhost:9090) in your web browser to access the Prometheus interface.

- **Access Grafana UI:**

  
```bash
  kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
  ```


  Open [http://localhost:3000](http://localhost:3000) and log in with the default credentials:

  - **Username:** admin

  - **Password:** prom 
