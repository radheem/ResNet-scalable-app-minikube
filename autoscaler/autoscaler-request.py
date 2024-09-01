import time
import logging
from flask import Flask
from kubernetes import client, config
import requests
from dotenv import load_dotenv
import os
from prometheus_client import Counter, generate_latest, REGISTRY, Summary, Histogram
# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

route_hit_counter = Counter('route_hits', 'Count of hits to routes', ['route'],registry=REGISTRY)
replica_counter = Counter('replica_counter', 'Count of replica', ['deplyment_name'],registry=REGISTRY)
app = Flask(__name__)


class AutoScaler:
    def __init__(self, prometheus_url, moving_average_duration, cooldown_period, deployment_name, namespace, latency_threshold_up, latency_threshold_down, count_threshold, max_replicas, min_replicas, MAX_FAILURES):
        self.PROMETHEUS_URL = prometheus_url
        self.MOVING_AVERAGE_DURATION = moving_average_duration
        self.COOLDOWN_PERIOD = cooldown_period
        self.DEPLOYMENT_NAME = deployment_name
        self.NAMESPACE = namespace
        self.LATENCY_THRESHOLD_UP = latency_threshold_up
        self.LATENCY_THRESHOLD_DOWN = latency_threshold_down
        self.COUNT_THRESHOLD = count_threshold
        self.MAX_REPLICAS = max_replicas
        self.MIN_REPLICAS = min_replicas
        self.MAX_FAILURES = MAX_FAILURES
        self.failure_upscale = False
        self.failure_count = 0

        try:
            config.load_kube_config()
        except config.ConfigException:
            config.load_incluster_config()  

        self.apps_v1 = client.AppsV1Api()

    def query_prometheus(self, query):
        try:
            logger.info(f"Querying Prometheus with: {query}")
            response = requests.get(f"{self.PROMETHEUS_URL}/api/v1/query", params={'query': query})
            response.raise_for_status()
            data = response.json()['data']
            
            result = data.get('result', [])
            
            if result:
                value = result[0].get('value', [])[1]
                logger.info(f"Value extracted: {value}")
                return float(value) 
                
            else:
                logger.warning(f"No results found for query: {query}")
                return None
            
        except requests.RequestException as e:
            logger.error(f"Error querying Prometheus: {e}")
            return None

    def get_metrics(self):
        try:
            # Query for 1-minute latency
            query_latency_avg = (
                f"max_over_time("
                f"  sum by (namespace, pod) ("
                f"    rate(request_latency_seconds_sum{{endpoint='/predict'}}[{self.MOVING_AVERAGE_DURATION}])"
                f"    /"
                f"    rate(request_latency_seconds_count{{endpoint='/predict'}}[{self.MOVING_AVERAGE_DURATION}])"
                f"  )[1m:]"
                f")"
            )

            latency_avg = self.query_prometheus(query_latency_avg)
            if latency_avg is None:
                logger.error("Failed to retrieve 1-minute moving average latency.")

            # Query for total count of requests for /predict endpoint over past 1 minute
            query_request_count = (
                f"sum(rate(request_latency_seconds_count{{endpoint='/predict'}}[1m]))"
            )

            request_count = self.query_prometheus(query_request_count)
            if request_count is None:
                logger.error("Failed to retrieve total request count for /predict endpoint.")

            if latency_avg is None or request_count is None:
                self.failure_count += 1
                if self.failure_count > self.MAX_FAILURES:
                    self.failure_upscale = True
                    self.failure_count = 0
                return None

            return latency_avg, request_count

        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            self.failure_count += 1
            if self.failure_count > self.MAX_FAILURES:
                self.failure_upscale = True
                self.failure_count = 0
            return None

    def scale_deployment(self, replicas):
        try:
            body = {
                "spec": {
                    "replicas": replicas
                }
            }
            self.apps_v1.patch_namespaced_deployment_scale(
                name=self.DEPLOYMENT_NAME,
                namespace=self.NAMESPACE,
                body=body
            )
            logger.info(f"Successfully scaled deployment to {replicas} replicas.")
        except Exception as e:
            logger.error(f"Error scaling deployment: {e}")

    def autoscale(self):
        while True:
            metrics = self.get_metrics()
            if metrics is None:
                if self.failure_upscale:
                    try:
                        deployment = self.apps_v1.read_namespaced_deployment(name=self.DEPLOYMENT_NAME, namespace=self.NAMESPACE)
                        current_replicas = deployment.spec.replicas
                        replica_counter.labels(deployment_name=self.DEPLOYMENT_NAME).inc(current_replicas)
                        if current_replicas < self.MAX_REPLICAS:
                            new_replicas = min(current_replicas + 1, self.MAX_REPLICAS)
                            logger.info(f"Scaling up due to persistent failures to {new_replicas} replicas")
                            self.scale_deployment(new_replicas)
                            self.failure_upscale = False
                    except Exception as e:
                        logger.error(f"Error reading or scaling deployment during failure upscale: {e}")
                time.sleep(self.COOLDOWN_PERIOD)
                continue

            latency_avg, request_count = metrics
            self.failure_count = 0
            try:
                deployment = self.apps_v1.read_namespaced_deployment(name=self.DEPLOYMENT_NAME, namespace=self.NAMESPACE)
                current_replicas = deployment.spec.replicas

                logger.info(f"Current 1-minute moving average latency: {latency_avg} seconds")
                logger.info(f"Current request count: {request_count}")
                logger.info(f"Current replicas: {current_replicas}")

                # Scaling logic
                if (latency_avg > self.LATENCY_THRESHOLD_UP or request_count > self.COUNT_THRESHOLD) and current_replicas < self.MAX_REPLICAS:
                    new_replicas = min(current_replicas + 1, self.MAX_REPLICAS)
                    logger.info(f"Scaling up to {new_replicas} replicas")
                    self.scale_deployment(new_replicas)
                elif latency_avg < self.LATENCY_THRESHOLD_DOWN and current_replicas > self.MIN_REPLICAS:
                    new_replicas = max(current_replicas - 1, self.MIN_REPLICAS)
                    logger.info(f"Scaling down to {new_replicas} replicas")
                    self.scale_deployment(new_replicas)

            except Exception as e:
                logger.error(f"Error reading or scaling deployment: {e}")

            time.sleep(self.COOLDOWN_PERIOD)

def create_autoscaler():
    # Initialize AutoScaler with required parameters
    env_path = os.path.join(os.path.dirname(__file__), '../.env')
    load_dotenv(env_path)
    PROMETHEUS_URL = os.getenv('PROMETHEUS_URL')
    MOVING_AVERAGE_DURATION = os.getenv('MOVING_AVERAGE_DURATION')
    COOLDOWN_PERIOD = int(os.getenv('COOLDOWN_PERIOD'))
    DEPLOYMENT_NAME = os.getenv('DEPLOYMENT_NAME')
    NAMESPACE = os.getenv('NAMESPACE')
    LATENCY_THRESHOLD_UP = float(os.getenv('LATENCY_THRESHOLD_UP'))
    LATENCY_THRESHOLD_DOWN = float(os.getenv('LATENCY_THRESHOLD_DOWN'))
    COUNT_THRESHOLD = int(os.getenv('COUNT_THRESHOLD'))
    MAX_REPLICAS = int(os.getenv('MAX_REPLICAS'))
    MIN_REPLICAS = int(os.getenv('MIN_REPLICAS'))
    MAX_FAILURES = int(os.getenv('MAX_FAILURES'))
    autoscaler = AutoScaler(
        prometheus_url=PROMETHEUS_URL,
        moving_average_duration=MOVING_AVERAGE_DURATION,
        cooldown_period=COOLDOWN_PERIOD,
        deployment_name=DEPLOYMENT_NAME,
        namespace=NAMESPACE,
        latency_threshold_up=LATENCY_THRESHOLD_UP,
        latency_threshold_down=LATENCY_THRESHOLD_DOWN,
        count_threshold=COUNT_THRESHOLD,
        max_replicas=MAX_REPLICAS,
        min_replicas=MIN_REPLICAS,
        MAX_FAILURES=MAX_FAILURES
    )
    return autoscaler


@app.route('/metrics')
def metrics():
    route_hit_counter.labels(route='/metrics').inc()
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/')
def index():
    route_hit_counter.labels(route='/').inc()
    return "<h1>Hello, Hope all good!</h1>"

if __name__ == "__main__":
    autoscaler = create_autoscaler()    
    autoscaler.autoscale()
    app.run(host='0.0.0.0', port=3000)
    
