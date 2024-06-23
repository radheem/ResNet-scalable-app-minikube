from flask import Flask, request, jsonify, redirect, Response
import io
from PIL import Image
from ResNet18 import ImageClassifier 
from prometheus_client import Counter, generate_latest, REGISTRY
from prometheus_client.exposition import start_http_server
from redis import Redis
from os import environ, path
import json

# Get environment variables with default values
redis_host = environ.get('REDIS_HOST', 'localhost')
redis_port = int(environ.get('REDIS_PORT', 6379))
app_port = int(environ.get('PORT', 5000))
metrics_port = int(environ.get('METRICS_PORT', 8000))

app = Flask(__name__)
redis = Redis(host=redis_host, port=redis_port)

# Assuming the ImagePredictor is correctly implemented
classifier = ImageClassifier()
# Define a Prometheus counter for tracking hits
route_hit_counter = Counter('route_hits', 'Count of hits to routes', ['route'])

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/predict', methods=['POST'])
def upload_file():
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
def index():
    route_hit_counter.labels(route='/').inc()
    redis.incr('/')
    return "<h1>Hello, I am working fine!</h1>"

@app.route('/counter')
def counter():
    redis.incr('/counter')
    route_hit_counter.labels(route='/counter').inc()
    count = redis.get('/counter').decode('utf-8')
    return f"visited {count} times"

@app.route('/redis')
def redis_data():
    data = {
        "/": redis.get('/').decode('utf-8') if redis.get('/') else 0,
        "/counter": redis.get('/counter').decode('utf-8') if redis.get('/counter') else 0,
        "/metrics": redis.get('/metrics').decode('utf-8') if redis.get('/metrics') else 0
    }
    return json.dumps(data)

@app.route('/metrics')
def metrics():
    redis.incr('/metrics')
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    # Start the Prometheus metrics server on the specified port
    start_http_server(metrics_port)
    app.run(host="0.0.0.0", port=app_port)
