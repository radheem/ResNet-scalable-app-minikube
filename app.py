from flask import Flask, request, jsonify
import io
from PIL import Image
from  ResNet18 import ImageClassifier 
from prometheus_client import Counter, generate_latest, REGISTRY
from prometheus_client.exposition import start_http_server
from redis import Redis
from os import environ
import json

app = Flask(__name__)

# Assuming the ImagePredictor is correctly implemented
classifier = ImageClassifier()

@app.route('/predict', methods=['POST'])
def image_prediction():
    # Check if there is data in the request
    if not request.data:
        return jsonify({'error': 'No data in the request'}), 400

    # Try to open the image from the raw binary data
    try:
        image = Image.open(io.BytesIO(request.data))
    except Exception as e:
        return jsonify({'error': 'Invalid image data'}), 400

    # Perform the prediction
    try:
        results = classifier.predict(image, topk=2)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify(results), 200


# Get environment variables with default values
redis_host = environ.get('REDIS_HOST', 'localhost')
redis_port = int(environ.get('REDIS_PORT', 6379))
app_port = int(environ.get('PORT', 5000))
metrics_port = int(environ.get('METRICS_PORT', 8000))

app = Flask(__name__)
redis = Redis(host=redis_host, port=redis_port)

# Define a Prometheus counter for tracking hits
route_hit_counter = Counter('route_hits', 'Count of hits to routes', ['route'])

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
