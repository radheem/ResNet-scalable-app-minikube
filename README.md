## Step1: Setup Steps
1. ```bash
    python3 scripts/load_model.py
    ```
2. ``` bash
    docker build -t resnet18-flask-app:latest .
    ```
3. ``` bash
    minikube start --driver=docker
    ```
4. ``` bash
    minikube image load resnet18-flask-app:latest
    ```
5. ``` bash
    chmod +x scripts/apply-prometheus-crds.sh
    ```
6. ``` bash
    ./scripts/apply-prometheus-crds.sh
    ```
7. ``` bash
    kubectl apply -f deployments/
    ``` 
8. ```bash 
    minikube tunnel
    ```

## Step2: Verify deployment
1. Go to any browser 
2. Visit localhost

## access minikube dashboard using
- minikube dashboard

# Notes 
- The match label is flask-app