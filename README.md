## Setup Steps
1. run ```docker build -t resnet18-flask-app:latest .```
2. run ```minikube start --driver=docker```
3. run ```minikube image load resnet18-flask-app:latest```
4. run ```chmod +x scripts/apply-prometheus-crds.sh```
5. run ```./scripts/apply-prometheus-crds.sh```
6. run ```kubectl create -f deployments/``` if creating else run ```kubectl apply -f deployments/``` to update configuration 
7. run ```minikube tunnel```

## access prometheus dashboard using 
- ```kubectl port-forward service/prometheus 9090:9090```

## access minikube dashboard using
- minikube dashboard

# Notes 
- The match label is flask-app