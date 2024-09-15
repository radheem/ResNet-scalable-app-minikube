import psycopg2
from psycopg2 import OperationalError, InterfaceError, DatabaseError, Error
from time import sleep
import logging

class PostgresConnectionManager:
    def __init__(self, host, port, database, user, password, max_retries=5, retry_delay=2):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection = None

    def connect(self):
        retries = 0
        while retries < self.max_retries:
            try:
                self.connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password
                )
                logging.info("Successfully connected to PostgreSQL")
                return self.connection
            except (OperationalError, InterfaceError) as e:
                retries += 1
                logging.warning(f"Connection attempt {retries} failed: {e}")
                sleep(self.retry_delay)
            except Exception as e:
                logging.error(f"Failed to connect to PostgreSQL: {e}")
                raise e
        logging.error("Exceeded maximum retries, could not connect to PostgreSQL")
        raise ConnectionError("Could not connect to PostgreSQL after multiple attempts.")

    def get_connection(self):
        if self.connection is None or self.connection.closed:
            logging.info("No active connection. Attempting to connect/reconnect.")
            self.connect()
        return self.connection

    def execute_query(self, query, params=None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                # If the query is a SELECT statement, fetch results
                if query.strip().upper().startswith("SELECT"):
                    return cursor.fetchall()
                else:
                    return None  # No results to fetch for INSERT, UPDATE, DELETE
        except (OperationalError, InterfaceError) as e:
            logging.warning(f"Connection error during query execution: {e}. Reconnecting.")
            self.connect()
            return self.execute_query(query, params)
        except Error as e:
            logging.error(f"Database error: {e}")
            conn.rollback()
            raise e


    def close(self):
        if self.connection and not self.connection.closed:
            try:
                self.connection.close()
                logging.info("PostgreSQL connection closed.")
            except Error as e:
                logging.error(f"Error closing PostgreSQL connection: {e}")
                raise e

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
