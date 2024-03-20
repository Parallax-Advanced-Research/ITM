from flask import Blueprint

probe_blueprint = Blueprint("probe", __name__, template_folder="templates")

from app.probe import views
