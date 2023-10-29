from flask import Blueprint

scenario_blueprint = Blueprint("scenario", __name__, template_folder="templates")

from app.scenario import views
