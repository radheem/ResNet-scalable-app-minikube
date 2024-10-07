import threading
import time
from flask import Flask, g, jsonify, request
import json
import io
import base64
import logging
from PIL import Image
from prometheus_client import REGISTRY, Counter, Histogram, Summary, generate_latest, start_http_server
from postgresConnector import PostgresConnectionManager
from rabbitmqConnector import RabbitMQConnectionManager
from classifier import ImageClassifier
from os import environ, path

# Load environment variables
db_host = environ.get('DB_HOST', 'localhost')
db_port = int(environ.get('DB_PORT', 5432))
db_name = environ.get('DB_NAME', 'resnet18_db')
db_user = environ.get('DB_USER', 'root')
db_password = environ.get('DB_PASSWORD', 'password')
rabbitmq_host = environ.get('RABBITMQ_HOST', 'localhost')
rabbitmq_queue = environ.get('RABBITMQ_QUEUE', 'requests_queue')
rabbitmq_username = environ.get('RABBITMQ_USERNAME', 'guest')   
rabbitmq_password = environ.get('RABBITMQ_PASSWORD', 'guest')
app_port = int(environ.get('PORT', 5000))
metrics_port = int(environ.get('METRICS_PORT', 8000))

app = Flask(__name__)

# Initialize the database manager
db_manager = PostgresConnectionManager(
    host=db_host,
    port=db_port,
    database=db_name,
    user=db_user,
    password=db_password
)

# Initialize the image classifier
model_path = path.join(path.dirname(__file__), '../models/resnet18.pth')
label_path = path.join(path.dirname(__file__), '../data/imagenet_classes.txt')
classifier = ImageClassifier(model_name='resnet18', model_path=model_path, label_path=label_path)

# initialize the RabbitMQ connection manager
rabbitmq_manager = RabbitMQConnectionManager(
    host=rabbitmq_host,
    queue_name=rabbitmq_queue,
    rabbitmq_username=rabbitmq_username,
    rabbitmq_password=rabbitmq_password
)

route_hit_counter = Counter('route_hits', 'Count of hits to routes', ['route'])
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request', registry=REGISTRY)
REQUEST_COUNT = Counter('request_count', 'Total number of requests', ['method', 'endpoint', 'http_status'], registry=REGISTRY)
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['method', 'endpoint'], registry=REGISTRY)

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    latency = time.time() - g.start_time
    REQUEST_LATENCY.labels(request.method, request.path).observe(latency)
    REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    response = {
        "error": str(e),
        "message": "An unexpected error occurred. Please try again later."
    }
    return jsonify(response), 500


@app.route('/')
@REQUEST_TIME.time()
def index():
    route_hit_counter.labels(route='/').inc()
    return "<h1>Hello, worker here!</h1>"

@app.route('/health')
def health():
    route_hit_counter.labels(route='/health').inc()
    return "OK", 200

@app.route('/metrics')
def metrics():
    route_hit_counter.labels(route='/metrics').inc()
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain; charset=utf-8'}

def start_flask_app():
    app.run(host='0.0.0.0', port=app_port)

def start_metrics_server():
    start_http_server(metrics_port)

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        request_id = message['id']
        encoded_image = message['image']
        
        # Decode image from base64
        image_data = base64.b64decode(encoded_image)
        image = Image.open(io.BytesIO(image_data))
        
        # Classify image
        results = classifier.predict(image, topk=1)
        label = results[0][0]
        confidence = results[0][1]  
        
        # Update the database with the label
        db_manager.execute_query(
            "UPDATE classification_requests SET status = %s, label = %s, confidence = %s WHERE id = %s",
            ('PROCESSED', label, confidence, request_id)
        )
        
        logging.info(f"Processed request ID {request_id} with label {label}")
        
        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.error(f"Failed to process message: {e}")
        # Optionally reject the message
        ch.basic_nack(delivery_tag=method.delivery_tag)

def start_consuming():
    rabbitmq_manager.connect()
    channel = rabbitmq_manager.get_channel()
    channel.basic_consume(queue=rabbitmq_queue, on_message_callback=callback)
    
    logging.info("Starting to consume messages...")
    channel.start_consuming()

def main():
    # Start the Prometheus metrics server in a separate thread
    threading.Thread(target=start_metrics_server).start()

    # Start the Flask app in a separate thread
    threading.Thread(target=start_flask_app).start()

    # Start RabbitMQ consumer in the main thread
    start_consuming()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
