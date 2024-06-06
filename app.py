from flask import Flask
from redis import Redis
from os import environ

redis_host = environ.get('REDIS_HOST', 'localhost')
redis_port = environ.get('REDIS_PORT', 6379)

app = Flask(__name__)
redis = Redis(host=redis_host, port=redis_port)

@app.route('/')
def hello():
    redis.incr('hits')
    return 'Hello World! I have been seen %s times.' % redis.get('hits')

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)