from dotenv import load_dotenv
import os

# load environment variables from .env file
load_dotenv()
from flask import Flask
from redis import Redis

app = Flask(__name__)
redis_host = os.getenv("HOST")
redis_port = os.getenv("PORT")
def connect_redis():
    try:
        redis = Redis(host=redis_port, port=redis_port, db=0, socket_timeout=5)
        redis.ping()
        return redis
    except Exception as e:
        print("Error: ", e)
        return False
    
redis = connect_redis()

@app.route('/counter')
def redisFunc():
    global redis
    if not redis:
        redis = connect_redis()
        if not redis:
            return "Error connecting to Redis"
    redis.incr('hits')
    counter = str(redis.get('hits'),'utf-8')
    return f"Welcome to Redis test!, view count: " + counter

@app.route('/')
def hello():
    return f"Welcome to redis: port>30379 . Hit /counter to test view count" 


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
