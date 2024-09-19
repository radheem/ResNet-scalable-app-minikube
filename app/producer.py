import io
from PIL import Image
from flask import Flask, request, jsonify, g
from uuid import uuid4
import json
import time
import logging
import base64
from os import environ
from prometheus_client import Counter, generate_latest, REGISTRY, Summary, Histogram
from prometheus_client.exposition import start_http_server

from app.constants import ALLOWED_EXTENSIONS
from app.postgresConnector import PostgresConnectionManager
from app.rabbitmqConnector import RabbitMQConnectionManager

################
### PRODUCER ###
################

# Environment variables for database and RabbitMQ
db_host = environ.get('DB_HOST', 'localhost')
db_port = int(environ.get('DB_PORT', 5432))
db_name = environ.get('DB_NAME', 'resnet18_db')
db_user = environ.get('DB_USER', 'postgres')
db_password = environ.get('DB_PASSWORD', 'password')
rabbitmq_host = environ.get('RABBITMQ_HOST', 'localhost')
rabbitmq_queue = environ.get('RABBITMQ_QUEUE', 'requests_queue')

# Prometheus metrics
route_hit_counter = Counter('route_hits', 'Count of hits to routes', ['route'])
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request', registry=REGISTRY)
REQUEST_COUNT = Counter('request_count', 'Total number of requests', ['method', 'endpoint', 'http_status'], registry=REGISTRY)
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['method', 'endpoint'], registry=REGISTRY)

# Initialize Flask app
app = Flask(__name__)

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    latency = time.time() - g.start_time
    REQUEST_LATENCY.labels(request.method, request.path).observe(latency)
    REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    return response

def initialize_connections():
    print("Initilizing Connections")
    """Initialize database and RabbitMQ connections at startup."""
    try:
        db_manager.connect()
        rabbitmq_manager.connect()
    except Exception as e:
        logging.error(f"Failed to initialize connections: {e}")
        raise

# Establish connections to PostgreSQL and RabbitMQ
db_manager = PostgresConnectionManager(
    host=db_host,
    port=db_port,
    database=db_name,
    user=db_user,
    password=db_password
)

rabbitmq_manager = RabbitMQConnectionManager(
    host=rabbitmq_host,
    queue_name=rabbitmq_queue
)

# Call connection initialization during app startup
initialize_connections()

@app.route('/predict', methods=['POST'])
@REQUEST_TIME.time()
def predict():
    route_hit_counter.labels(route='/predict').inc()
    try:
        resp = {'msg': 'Image not found in request', 'hint': 'Add the image to a key named "image"'}
        if 'image' not in request.files:
            return jsonify(resp), 400
        
        file = request.files['image']    
        try:
            image = Image.open(io.BytesIO(file.read())) 
            image_bytes = io.BytesIO()
            image.save(image_bytes, format=image.format)
            encoded_image = base64.b64encode(image_bytes.getvalue()).decode('utf-8')  # Base64 encoding
        except Exception as e:
            resp = {'msg': 'Invalid image data', 'hint': f'The image may not be of a valid extension {ALLOWED_EXTENSIONS}', 'error': str(e)}
            return jsonify(resp), 400
        
        request_id = str(uuid4())

        # Insert request into PostgreSQL database
        db_manager.execute_query(
            "INSERT INTO requests (id, status, label) VALUES (%s, %s, %s)",
            (request_id, 'PENDING', None)
        )
        # Publish message to RabbitMQ
        rabbitmq_manager.publish_message(json.dumps({'id': request_id, 'image': encoded_image}))
        return jsonify({'id': request_id}), 200

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/predict', methods=['GET'])
@REQUEST_TIME.time()
def get_prediction():
    route_hit_counter.labels(route='/predict').inc()
    try:
        request_id = request.args.get('id')
        if not request_id:
            return jsonify({'msg': 'Request ID not found in query parameters', 'hint': 'Add the request ID to the query parameter "id"'}), 400
        
        result = db_manager.execute_query(
            "SELECT * FROM requests WHERE id = %s",
            (request_id,)
        )
        if not result:
            return jsonify({'msg': 'Request ID not found', 'hint': 'Check the request ID and try again'}), 404
        
        return jsonify({'id': result[0], 'status': result[1], 'label': result[2]}), 200

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    route_hit_counter.labels(route='/health').inc()
    return "OK", 200

@app.route('/metrics')
def metrics():
    route_hit_counter.labels(route='/metrics').inc()
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain; charset=utf-8'}

def start_metrics_server():
    start_http_server(8000)

if __name__ == '__main__':
    start_metrics_server()  # Start the Prometheus metrics server
    app.run(host='0.0.0.0', port=5001)
