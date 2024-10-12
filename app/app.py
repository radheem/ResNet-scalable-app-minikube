import io
from PIL import Image
from flask import Flask, request, jsonify, g, render_template
import json
import time
import logging
import base64
from os import environ
from models import db, ClassificationRequest
from prometheus_client import Counter, generate_latest, REGISTRY, Summary, Histogram
from prometheus_client.exposition import start_http_server

from constants import ALLOWED_EXTENSIONS
from postgresConnector import PostgresConnectionManager
from rabbitmqConnector import RabbitMQConnectionManager
from flask_migrate import Migrate


# Environment variables for database and RabbitMQ
db_host = environ.get('DB_HOST', 'localhost')
db_port = int(environ.get('DB_PORT', 5432))
db_name = environ.get('DB_NAME', 'resnet18_db')
db_user = environ.get('DB_USER', 'root')
db_password = environ.get('DB_PASSWORD', 'password')
rabbitmq_host = environ.get('RABBITMQ_HOST', 'localhost')
rabbitmq_port = int(environ.get('RABBITMQ_PORT', 5672))
rabbitmq_queue = environ.get('RABBITMQ_QUEUE', 'requests_queue')
rabbitmq_username = environ.get('RABBITMQ_USERNAME', 'guest')   
rabbitmq_password = environ.get('RABBITMQ_PASSWORD', 'guest')

route_hit_counter = Counter('route_hits', 'Count of hits to routes', ['route'])
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request', registry=REGISTRY)
REQUEST_COUNT = Counter('request_count', 'Total number of requests', ['method', 'endpoint', 'http_status'], registry=REGISTRY)
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['method', 'endpoint'], registry=REGISTRY)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

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
    """Initialize database and RabbitMQ connections at startup."""
    logging.info("Initializing connections...")
    try:
        db_manager.connect()
        rabbitmq_manager.connect()
        logging.info("Connections established successfully.")
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
    port=rabbitmq_port,
    queue_name=rabbitmq_queue,
    rabbitmq_username=rabbitmq_username,
    rabbitmq_password=rabbitmq_password
)

initialize_connections()

def predict(file):
    try:
        image = Image.open(io.BytesIO(file.read())) 
        if image.format.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Invalid image format: {image.format}")
        
        image_bytes = io.BytesIO()
        image.save(image_bytes, format=image.format)
        encoded_image = base64.b64encode(image_bytes.getvalue()).decode('utf-8')
    except Exception as e:
        resp = {'status': 400, 'header': 'Invalid image data', 'msg': 'The image may not be of a valid extension {}. Error: {}'.format(ALLOWED_EXTENSIONS,str(e))}
        return resp    
    
    try:
        record = ClassificationRequest(status='PENDING', label=None)
        db.session.add(record)
        db.session.commit()
        request_id = record.id
    except Exception as db_error:
        db.session.rollback()
        logging.error(f"Failed to save classification request to the database: {db_error}")
        data = {'status': 400, 'header': 'Database Error', 'msg': str(db_error)}
        return data

    try:
        msg = {'id': request_id, 'image': encoded_image} 
        rabbitmq_manager.publish_message(json.dumps(msg))
    except Exception as rabbitmq_error:
        logging.error(f"Failed to publish message to RabbitMQ: {rabbitmq_error}")
        data = {'status': 400, 'header':'RabbitMQ Error','msg': 'Failed to publish message to RabbitMQ. Error:{}'.format(str(rabbitmq_error))}
        return data
    data = {'status': 200, 'msg': 'Prediction request received. Request id:{}'.format(request_id)}
    return data

@app.route('/predictFE', methods=['POST'])
@REQUEST_TIME.time()
def predictFE():
    route_hit_counter.labels(route='/predict').inc()
    try:
        resp = {'header': 'Image not found in request', 'msg': 'Add the image to a key named "image"'}
        if 'image' not in request.files:
            return render_template('processing.html', data=resp)
        file = request.files['image']    
        data = predict(file)
        return render_template('processing.html', data=data), data['status']
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
@REQUEST_TIME.time()
def predictAPI():
    route_hit_counter.labels(route='/predict').inc()
    try:
        resp = {'header': 'Image not found in request', 'msg': 'Add the image to a key named "image"'}
        if 'image' not in request.files:
            return resp
        file = request.files['image']    
        data = predict(file)
        return data, data['status']
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/results', methods=['GET'])
@REQUEST_TIME.time()
def get_prediction():
    route_hit_counter.labels(route='/results').inc()
    try:
        route_hit_counter.labels(route='/results').inc()
        
        request_id = request.args.get('id')
        if request_id:
            result = db_manager.execute_query(
                "SELECT id, status, label FROM classification_requests WHERE id = %s",
                (request_id)
            )
            if not result:
                return jsonify({'msg': 'Request ID not found', 'hint': 'Check the request ID and try again'}), 404
            return jsonify({'id': result[0][0], 'status': result[0][1], 'label': result[0][2]}), 200
        
        cursor = request.args.get('cursor', None)
        limit = int(request.args.get('limit', 10))
        order = request.args.get('order', 'desc').lower()
        direction = request.args.get('direction', 'next').lower()
        order_clause = 'ASC' if order == 'asc' else 'DESC'
           
        query = 'SELECT id, status, label, "createdAt"\nFROM classification_requests'
        prev_cursor = None
        next_cursor = None   
        if cursor:
            if direction == 'next':
                prev_cursor = int(cursor) +1
                next_cursor = int(cursor) + limit
            else:
                prev_cursor = int(cursor) - limit - 1
                next_cursor = int(cursor) - 1
              
            query += "\nWHERE id >= {} AND id <= {}".format(str(prev_cursor), str(next_cursor))
        
        query += "\nORDER BY id {}\nLIMIT {}".format(order_clause, limit)
        results = db_manager.execute_query(query)

        data = [{'id': row[0], 'status': row[1], 'label': row[2], 'createdAt':row[3]} for row in results]
        has_more = True
        if len(data) < limit:
            has_more = False
        if len(data) > 0 and has_more:
            cursor = data[-1]['id']

        response = {
            'data': data,
            'limit': limit,
            'order': order,
            'cursor': int(cursor),
            'has_more': has_more,
            'direction': direction
        }
        return render_template('results.html', data=response)

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
@REQUEST_TIME.time()
def index():
    route_hit_counter.labels(route='/').inc()
    return render_template('index.html')

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
    # start_metrics_server()  # Start the Prometheus metrics server
    with app.app_context():
        db.create_all()    
    migrate = Migrate(app, db)
    app.run(host='0.0.0.0', port=5000, debug=True)  # Start the Flask app
    