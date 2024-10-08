import psycopg2
from psycopg2 import OperationalError, InterfaceError, DatabaseError, Error, sql
from time import sleep
import logging

class PostgresConnectionManager:
    def __init__(self, host, port, user, password, database=None, max_retries=5, retry_delay=2):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection = None

    def _create_db_if_not_exists(self):
        # Connect to the default 'postgres' database to check if the target DB exists
        print(f"Checking if database '{self.database}' exists...")
        conn = self._connect_to_default_db()
        cursor = conn.cursor()
        
        # Check if the database exists
        cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [self.database])
        exists = cursor.fetchone()

        if not exists:
            print(f"Database '{self.database}' does not exist. Creating it now.")
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.database)))
            print(f"Database '{self.database}' created successfully.")
        else:
            print(f"Database '{self.database}' already exists.")
        
        cursor.close()
        conn.close()

    def _connect_to_default_db(self):
        """Connect to the 'postgres' default database for management tasks like creating databases."""
        retries = 0
        while retries < self.max_retries:
            try:
                conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database="postgres"  # Connect to default 'postgres' database
                )
                conn.autocommit = True
                logging.info("Connected to the default 'postgres' database")
                return conn
            except (OperationalError, InterfaceError) as e:
                retries += 1
                logging.warning(f"Connection to default database failed. Attempt {retries}: {e}")
                sleep(self.retry_delay)
            except Exception as e:
                logging.error(f"Failed to connect to default 'postgres' database: {e}")
                raise e
        logging.error("Exceeded maximum retries, could not connect to 'postgres' database")
        raise ConnectionError("Could not connect to default database after multiple attempts.")

    def connect(self, database=None):
        retries = 0
        if self.database is None and database is None:
            raise ValueError("Database name must be provided.")
        if database:
            self.database = database

        # Ensure the database exists
        self._create_db_if_not_exists()

        while retries < self.max_retries:
            try:
                self.connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database
                )
                self.connection.autocommit = True
                logging.info(f"Successfully connected to PostgreSQL database '{self.database}'")
                return self.connection
            except (OperationalError, InterfaceError) as e:
                retries += 1
                logging.warning(f"Connection attempt {retries} to '{self.database}' failed: {e}")
                sleep(self.retry_delay)
            except Exception as e:
                logging.error(f"Failed to connect to PostgreSQL database '{self.database}': {e}")
                raise e
        logging.error(f"Exceeded maximum retries, could not connect to database '{self.database}'")
        raise ConnectionError(f"Could not connect to PostgreSQL database '{self.database}' after multiple attempts.")

    def get_connection(self):
        """Get the active connection or reconnect if necessary."""
        if not self.connection or self.connection.closed:
            logging.info("No active connection. Attempting to connect/reconnect.")
            self.connect()
        return self.connection

    def execute_query(self, query, params=None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                # Commit for non-SELECT queries
                if not query.strip().upper().startswith("SELECT"):
                    conn.commit()
                # Return results for SELECT queries
                if query.strip().upper().startswith("SELECT"):
                    return cursor.fetchall()
        except (OperationalError, InterfaceError) as e:
            logging.warning(f"Connection error during query execution: {e}. Reconnecting.")
            self.connect()  # Attempt to reconnect and retry
            return self.execute_query(query, params)
        except Error as e:
            logging.error(f"Database error: {e}")
            conn.rollback()  # Rollback in case of error
            raise e

    def close(self):
        """Close the PostgreSQL connection if it is active."""
        if self.connection and not self.connection.closed:
            try:
                self.connection.close()
                logging.info("PostgreSQL connection closed.")
            except Error as e:
                logging.error(f"Error closing PostgreSQL connection: {e}")
                raise e

    def __enter__(self):
        """Enter context management and establish the connection."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit context management and close the connection."""
        self.close()
