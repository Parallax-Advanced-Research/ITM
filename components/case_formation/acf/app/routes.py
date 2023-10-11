from components.case_formation.acf.app import app
from flask import render_template


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html", title="Home")


@app.route("/create/case_base")
def create_case_base():
    return render_template("create_case_base.html", title="Create Case Base")


@app.route("/create/case")
def create_case():
    return render_template("create_case.html", title="Create Case")
