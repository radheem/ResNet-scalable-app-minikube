import io
from PIL import Image
from flask import Flask, request, jsonify
from uuid import uuid4
import json
from os import environ
import logging
from app.constants import ALLOWED_EXTENSIONS

from postgresConnector import PostgresConnectionManager
from rabbitmqConnector import RabbitMQConnectionManager

db_host = environ.get('DB_HOST', 'localhost')
db_port = int(environ.get('DB_PORT', 5432))
db_name = environ.get('DB_NAME', 'resnet18_db')
db_user = environ.get('DB_USER', 'postgres')
db_password = environ.get('DB_PASSWORD', 'password')
rabbitmq_host = environ.get('RABBITMQ_HOST', 'localhost')
rabbitmq_queue = environ.get('RABBITMQ_QUEUE', 'requests_queue')

app = Flask(__name__)

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

@app.route('/predict', methods=['POST'])
def predict():
    try:
        resp = {'msg': 'Image not found in request', 'hint': 'Add the image to a key named "image"'}
        if 'image' not in request.files:
            return jsonify(resp), 400
        
        file = request.files['image']    
        try:
            image = Image.open(io.BytesIO(file.read())) 
        except Exception as e:
            resp = {'msg': 'Invalid image data', 'hint': f'The image may not be of a valid extension {ALLOWED_EXTENSIONS}', 'error': str(e)}
            return jsonify(resp), 400
        
        request_id = str(uuid4())
        
        db_manager.execute_query(
            "INSERT INTO requests (id, status, label) VALUES (%s, %s)",
            (request_id, 'PENDING', None)
        )

        rabbitmq_manager.publish_message(json.dumps({'id': request_id, 'image': image}))

        return jsonify({'id': request_id}), 200

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/predict', methods=['GET'])
def get_prediction():
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
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
