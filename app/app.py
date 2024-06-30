import time
from flask import Flask, request, jsonify, g
import io
from PIL import Image
from app.classifier import ImageClassifier 
from prometheus_client import Counter, generate_latest, REGISTRY, Summary, Histogram
from prometheus_client.exposition import start_http_server
from os import environ, path
from app.constants import ALLOWED_EXTENSIONS
from app.utils import allowed_file

# Load environment variables
app_port = int(environ.get('PORT', 5000))
metrics_port = int(environ.get('METRICS_PORT', 8000))

# Init app and classifier
app = Flask(__name__)
app.config['DEBUG'] = False
model_path = path.join(path.dirname(__file__), '../models/resnet18.pth')
label_path = path.join(path.dirname(__file__), '../data/imagenet_classes.txt')
classifier = ImageClassifier(model_name='resnet18', model_path=model_path,label_path=label_path)

# Prometheus metrics
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

@app.route('/predict', methods=['POST'])
@REQUEST_TIME.time()
def predict():
    route_hit_counter.labels(route='/predict').inc()
    resp = {'msg': 'Image not found in request', 'hint': 'Add the image to a key named "image"'}
    if 'image' not in request.files:
        return jsonify(resp), 400
    
    file = request.files['image']    
    try:
        image = Image.open(io.BytesIO(file.read())) 
    except Exception as e:
        resp = {'msg': 'Invalid image data', 'hint': f'The image may not be of a valid extension {ALLOWED_EXTENSIONS}', 'error': str(e)}
        return jsonify(resp), 400
    
    try:
        print("Predicting image")
        results = classifier.predict(image, topk=2)
        print("Done")
    except Exception as e:
        resp = {'msg': 'Failed to classify', 'error': str(e)}
        return jsonify(resp), 500
    
    confidence = results[0][1] * 100  
    label = results[0][0]
    return jsonify({'msg': f"I am {confidence:.2f} % confident that it is a {label}."}), 200

@app.route('/')
@REQUEST_TIME.time()
def index():
    route_hit_counter.labels(route='/').inc()
    return "<h1>Hello, Hope all good!</h1>"

@app.route('/health')
def health():
    route_hit_counter.labels(route='/health').inc()
    return "OK", 200

@app.route('/metrics')
def metrics():
    route_hit_counter.labels(route='/metrics').inc()
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain; charset=utf-8'}


def start_metrics_server():
    start_http_server(metrics_port)

