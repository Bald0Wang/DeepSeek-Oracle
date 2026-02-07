from flask import Flask

from .analyze import analyze_bp
from .export import export_bp
from .history import history_bp
from .task import task_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(analyze_bp, url_prefix="/api")
    app.register_blueprint(task_bp, url_prefix="/api")
    app.register_blueprint(history_bp, url_prefix="/api")
    app.register_blueprint(export_bp, url_prefix="/api")
