from asyncio import sleep
import pika
import json
import io
import base64
import logging
from PIL import Image
from postgresConnector import PostgresConnectionManager
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

# RabbitMQ connection setup
class RabbitMQConnectionManager:
    def __init__(self, host, queue_name, max_retries=5, retry_delay=2):
        self.host = host
        self.queue_name = queue_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection = None
        self.channel = None

    def connect(self):
        retries = 0
        while retries < self.max_retries:
            try:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=self.queue_name, durable=True)
                logging.info("Successfully connected to RabbitMQ")
                return
            except pika.exceptions.AMQPConnectionError as e:
                retries += 1
                logging.warning(f"Connection attempt {retries} failed: {e}")
                sleep(self.retry_delay)
            except Exception as e:
                logging.error(f"Failed to connect to RabbitMQ: {e}")
                raise e
        logging.error("Exceeded maximum retries, could not connect to RabbitMQ")
        raise ConnectionError("Could not connect to RabbitMQ after multiple attempts.")

    def get_channel(self):
        if self.connection is None or self.connection.is_closed or self.channel is None or self.channel.is_closed:
            logging.info("No active RabbitMQ connection. Attempting to connect/reconnect.")
            self.connect()
        return self.channel

    def close(self):
        if self.connection and not self.connection.is_closed:
            try:
                self.connection.close()
                logging.info("RabbitMQ connection closed.")
            except Exception as e:
                logging.error(f"Error closing RabbitMQ connection: {e}")
                raise e

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

rabbitmq_manager = RabbitMQConnectionManager(
    host=rabbitmq_host,
    queue_name=rabbitmq_queue
)

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

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_consuming()
