from gunicorn.app.base import BaseApplication
from app.app import app  
from os import environ

class FlaskApp(BaseApplication):
    def __init__(self, app, host, port, workers):
        self.application = app
        self.host = host
        self.port = port
        self.workers = workers
        super().__init__()

    def load_config(self):
        self.cfg.set('bind', f'{self.host}:{self.port}')
        self.cfg.set('workers', self.workers)

    def load(self):
        return self.application

if __name__ == '__main__':
    app_port = int(environ.get('PORT', 5000))
    host = '0.0.0.0'
    workers = int(environ.get('WORKERS', 1))  
    gunicorn_app = FlaskApp(app, host, app_port, workers)
    gunicorn_app.run()
