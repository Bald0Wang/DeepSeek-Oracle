from flask import Flask

from .admin import admin_bp
from .analyze import analyze_bp
from .auth import auth_bp
from .export import export_bp
from .history import history_bp
from .insights import insights_bp
from .oracle import oracle_bp
from .task import task_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(analyze_bp, url_prefix="/api")
    app.register_blueprint(task_bp, url_prefix="/api")
    app.register_blueprint(history_bp, url_prefix="/api")
    app.register_blueprint(export_bp, url_prefix="/api")
    app.register_blueprint(insights_bp, url_prefix="/api")
    app.register_blueprint(oracle_bp, url_prefix="/api")
