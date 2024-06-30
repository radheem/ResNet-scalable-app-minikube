## Step1: Setup Steps
1. ``` bash
    docker build -t resnet18-flask-app:latest .
    ```
2. ``` bash
    minikube start --driver=docker
    ```
3. ``` bash
    minikube image load resnet18-flask-app:latest
    ```
4. ``` bash
    chmod +x scripts/apply-prometheus-crds.sh
    ```
5. ``` bash
    ./scripts/apply-prometheus-crds.sh
    ```
6. ``` bash
    kubectl apply -f deployments/
    ``` 
7. ```bash 
    minikube tunnel
    ```

## Step2: Verify deployment
1. Go to any browser 
2. Visit localhost

## access minikube dashboard using
- minikube dashboard

# Notes 
- The match label is flask-app