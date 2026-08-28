from flask import Flask
import os
from .routes import register_routes

def create_app():
    app = Flask(__name__, template_folder='../template')
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY environment variable is not set")
    app.secret_key = secret
    register_routes(app)
    return app