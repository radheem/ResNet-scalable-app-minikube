import pika
import logging
from time import sleep

class RabbitMQConnectionManager:
    def __init__(self, host, port, queue_name, max_retries=5, retry_delay=2,rabbitmq_username="guest", rabbitmq_password="guest"):
        self.host = host
        self.port = port
        self.queue_name = queue_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection = None
        self.channel = None
        print('rabbit mq creds: {},{}'.format(rabbitmq_username, rabbitmq_password))
        self.credentials = pika.PlainCredentials(rabbitmq_username, rabbitmq_password)
        self.parameters = pika.ConnectionParameters(host=self.host, port=self.port, credentials=self.credentials)

    def connect(self):
        retries = 0
        while retries < self.max_retries:
            try:
                self.connection = pika.BlockingConnection(parameters=self.parameters)
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

    def publish_message(self, message):
        channel = self.get_channel()
        try:
            channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
            )
            logging.info(f"Message sent to RabbitMQ: {message}")
        except pika.exceptions.AMQPConnectionError as e:
            logging.warning(f"Connection error during message publish: {e}. Reconnecting.")
            self.connect()
            self.publish_message(message)
        except Exception as e:
            logging.error(f"Failed to publish message to RabbitMQ: {e}")
            raise e

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
