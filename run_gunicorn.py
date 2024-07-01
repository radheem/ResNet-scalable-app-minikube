from gunicorn.app.base import BaseApplication
from app.app import app  
from os import environ
import torch.multiprocessing as mp

mp.set_start_method('spawn')

class FlaskApp(BaseApplication):
    def __init__(self, app, host, port, workers, threads):
        self.application = app
        self.host = host
        self.port = port
        self.workers = workers
        self.threads = threads
        super().__init__()

    def load_config(self):
        self.cfg.set('bind', f'{self.host}:{self.port}')
        self.cfg.set('workers', self.workers)
        self.cfg.set('threads', self.threads)

    def load(self):
        return self.application

if __name__ == '__main__':
    app_port = int(environ.get('PORT', 5000))
    host = '0.0.0.0'
    workers = int(environ.get('WEB_CONCURRENCY', 2))  # Adjust based on your deployment environment
    threads = int(environ.get('THREADS', 2))
    gunicorn_app = FlaskApp(app, host, app_port, workers, threads)
    gunicorn_app.run()
