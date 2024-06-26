import time
from flask import Flask, request, jsonify, g
import io
from PIL import Image
from ResNet18 import ImageClassifier 
from prometheus_client import Counter, generate_latest, REGISTRY, Summary, Gauge, Histogram
from prometheus_client.exposition import start_http_server
from os import environ
from constants import ALLOWED_EXTENSIONS
from utils import allowed_file

# load environment variables
app_port = int(environ.get('PORT', 5000))
metrics_port = int(environ.get('METRICS_PORT', 8000))

# Init app and classifier
app = Flask(__name__)
classifier = ImageClassifier()

# Prometheus metrics
route_hit_counter = Counter('route_hits', 'Count of hits to routes', ['route'])
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request', registry=REGISTRY)
REQUEST_COUNT = Counter('request_count', 'Total number of requests',['method', 'endpoint', 'http_status'], registry=REGISTRY)
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['method', 'endpoint'], registry=REGISTRY)


@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    latency = time.time() - g.start_time
    REQUEST_LATENCY.labels(request.method, request.path).observe(latency)
    return response

@app.route('/predict', methods=['POST'])
@REQUEST_TIME.time()
def predict():
    route_hit_counter.labels(route='/predict').inc()
    resp = {'msg': 'image not found in request', 'hint': 'add the image to a key named image'}
    if 'image' not in request.files:
        return jsonify(resp), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify(resp), 400
    if file and not allowed_file(file.filename):
        resp = {'msg': 'invalid image data', 'hint': 'the image may not be of a valid extension'+ str(ALLOWED_EXTENSIONS)}
        return jsonify(resp), 400
        
    try:
        image = Image.open(io.BytesIO(file.read())) 
    except Exception as e:
        resp = {'msg': 'invalid image data', 'hint': 'the image may not be of a valid extension'+ str(ALLOWED_EXTENSIONS), 'error': str(e)}
        return jsonify(resp), 400
    
    try:
        results = classifier.predict(image, topk=2)
    except Exception as e:
        resp = {'msg': 'failed to classify', 'error': str(e)}
        return jsonify(resp), 400
    
    confidence = results[0][1] * 100  
    label = results[0][0]
    return f"I am {confidence:.2f} % confident that it is a {label}.", 200

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

if __name__ == '__main__':
    start_http_server(metrics_port)
    app.run(host="0.0.0.0", port=app_port)
