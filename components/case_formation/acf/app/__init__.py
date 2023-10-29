from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_bootstrap import Bootstrap5


db = SQLAlchemy()
migrate = Migrate()
bootstrap = Bootstrap5()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    migrate.init_app(app, db)
    bootstrap.init_app(app)

    from app.main import main_blueprint as main_bp
    from app.case import case_blueprint as case_bp
    from app.scenario import scenario_blueprint as scenario_bp
    from app.probe import probe_blueprint as probe_bp

    app.register_blueprint(main_bp, url_prefix="/")
    app.register_blueprint(case_bp, url_prefix="/case")
    app.register_blueprint(scenario_bp, url_prefix="/scenario")
    app.register_blueprint(probe_bp, url_prefix="/probe")

    from app.case.models import CaseBase
    from app.scenario.models import Scenario
    from app.scenario.models import Casualty
    from app.probe.models import Probe

    return app
