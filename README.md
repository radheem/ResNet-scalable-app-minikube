## Steps
1. minikube start
2. minikube image load resnet18-flask-app:latest
3. kubectl create -f deployments/
4. minikube tunnel

## access prometheus dashboard
- kubectl port-forward service/prometheus 9090:9090

## access minikube dashboard
- minikube dashboard