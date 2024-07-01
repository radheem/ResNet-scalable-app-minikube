import time
import requests
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging

# Load Kubernetes configuration
config.load_kube_config()

apps_v1 = client.AppsV1Api()

# Prometheus server URL
PROMETHEUS_URL = "http://localhost:9090"

# Configuration
NAMESPACE = 'default'
DEPLOYMENT_NAME = 'flask-app'
LATENCY_THRESHOLD_UP = 0.2  # Latency in seconds to scale up
LATENCY_THRESHOLD_DOWN = 0.5  # Latency in seconds to scale down
MIN_REPLICAS = 5
MAX_REPLICAS = 10
COOLDOWN_PERIOD = 10  # Time to wait before another scaling action (in seconds)
MOVING_AVERAGE_DURATION = "1m"  # Duration for moving average

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def query_prometheus(query):
    try:
        logger.info(f"Querying Prometheus with: {query}")
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query})
        response.raise_for_status()
        data = response.json()['data']
        
        # Assuming resultType is "vector" and there's only one result in your case
        result = data.get('result', [])
        
        if result:
            value = result[0].get('value', [])[1]
            logger.info(f"Value extracted: {value}")
            return float(value)  # Convert value to float if needed
            
        else:
            logger.warning(f"No results found for query: {query}")
            return None
        
    except requests.RequestException as e:
        logger.error(f"Error querying Prometheus: {e}")
        return None

def get_metrics():
    # Query for 1-minute moving average latency
    query_latency_avg = (
        f"  sum(rate(request_latency_seconds_sum{{endpoint='/predict'}}[{MOVING_AVERAGE_DURATION}]))"
        f"    /"
        f"  sum(rate(request_latency_seconds_count{{endpoint='/predict'}}[{MOVING_AVERAGE_DURATION}]))"
    )

    latency_avg = query_prometheus(query_latency_avg)
    if latency_avg is None:
        logger.error("Failed to retrieve 1-minute moving average latency. Skipping this cycle.")
        return None

    return latency_avg

def scale_deployment(replicas):
    try:
        deployment = apps_v1.read_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE)
        deployment.spec.replicas = replicas
        apps_v1.replace_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE, body=deployment)
        logger.info(f"Scaled deployment to {replicas} replicas")
    except ApiException as e:
        logger.error(f"Exception when scaling deployment: {e}")

def autoscale():
    while True:
        latency_avg = get_metrics()

        if latency_avg is None:
            logger.error("Failed to retrieve metrics. Skipping this cycle.")
            time.sleep(COOLDOWN_PERIOD)
            continue

        deployment = apps_v1.read_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE)
        current_replicas = deployment.spec.replicas

        logger.info(f"Current 1-minute moving average latency: {latency_avg} seconds")
        logger.info(f"Current replicas: {current_replicas}")

        if latency_avg > LATENCY_THRESHOLD_UP and current_replicas < MAX_REPLICAS:
            new_replicas = min(current_replicas + 1, MAX_REPLICAS)
            logger.info(f"Scaling up to {new_replicas} replicas")
            scale_deployment(new_replicas)
        elif latency_avg < LATENCY_THRESHOLD_DOWN and current_replicas > MIN_REPLICAS:
            new_replicas = max(current_replicas - 1, MIN_REPLICAS)
            logger.info(f"Scaling down to {new_replicas} replicas")
            scale_deployment(new_replicas)

        time.sleep(COOLDOWN_PERIOD)

if __name__ == "__main__":
    autoscale()
