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
from concurrent.futures import Future, TimeoutError
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
app_port = int(environ.get('PORT', 5000))
metrics_port = int(environ.get('METRICS_PORT', 8000))

# Init app and classifier
app = Flask(__name__)
app.config['DEBUG'] = False
model_path = path.join(path.dirname(__file__), '../models/resnet18.pth')
label_path = path.join(path.dirname(__file__), '../data/imagenet_classes.txt')
classifier = ImageClassifier(model_name='resnet18', model_path=model_path, label_path=label_path)

# Prometheus metrics
route_hit_counter = Counter('route_hits', 'Count of hits to routes', ['route'])
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request', registry=REGISTRY)
REQUEST_COUNT = Counter('request_count', 'Total number of requests', ['method', 'endpoint', 'http_status'], registry=REGISTRY)
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['method', 'endpoint'], registry=REGISTRY)

# Task queue and executor
executor = ThreadPoolExecutor(max_workers=1)

def process_task(task_id, image, future):
    print(f"process_task called for task {task_id}")
    try:
        print(f"Starting to process task {task_id}")
        results = classifier.predict(image, topk=2)
        print(f"Task {task_id} processed successfully with results: {results}")
        confidence = results[0][1] * 100  
        label = results[0][0]
        return {'msg': f"I am {confidence:.2f}% confident that it is a {label}."}
    except Exception as e:
        print(f"Exception in task {task_id}: {e}")
        raise

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
    if 'image' not in request.files:
        return jsonify({'msg': 'Image not found in request', 'hint': 'Add the image to a key named "image"'}), 400
    
    file = request.files['image']
    try:
        image = Image.open(io.BytesIO(file.read())) 
    except Exception as e:
        return jsonify({'msg': 'Invalid image data', 'hint': f'The image may not be of a valid extension {ALLOWED_EXTENSIONS}', 'error': str(e)}), 400
    
    # Create a unique task ID
    task_id = str(uuid.uuid4())    
    try:
        future = executor.submit(process_task, task_id, image, Future())
        result = future.result(timeout=2)
    except TimeoutError:
        return jsonify({'msg': 'Classification timed out', 'error': 'Task processing took too long'}), 500
    except Exception as e:
        return jsonify({'msg': 'Failed to classify', 'error': str(e)}), 500
    
    return jsonify(result), 200

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

if __name__ == '__main__':
    start_metrics_server()
    app.run(port=app_port)