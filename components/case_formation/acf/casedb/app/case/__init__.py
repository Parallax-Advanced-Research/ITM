from flask import Blueprint

case_blueprint = Blueprint("case", __name__, template_folder="templates")

from app.case import views
