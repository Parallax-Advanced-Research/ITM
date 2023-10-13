from components.case_formation.acf.app import app
from flask import render_template, redirect, url_for, flash
from app.forms import *
from app.models import *

from components.case_formation.acf.app import app
from components.case_formation.acf.app import db


@app.route("/")
@app.route("/index")
def index():
    return redirect(url_for("case_base"))


### Case bases
@app.route("/case_base/<int:case_base_id>")
def view_case_base(case_base_id):
    case_base = CaseBase.query.filter_by(id=case_base_id).first_or_404()
    return render_template(
        "case_base.html",
        case_base=case_base,
    )


@app.route("/case_base/list")
def case_base():
    pagination = CaseBase.query.paginate(page=1, per_page=10)
    case_bases = pagination.items
    return render_template(
        "case_bases.html",
        title="Case Bases",
        case_bases=case_bases,
    )


@app.route("/case_base/create", methods=["GET", "POST"])
def create_case_base():
    form = CaseBaseForm()
    if form.validate_on_submit():
        case_base = CaseBase(
            name=form.name.data, description=form.description.data, created_by="admin"
        )
        db.session.add(case_base)
        db.session.commit
        flash("Case Base Created")()
        return redirect(url_for("index"))
    return render_template(
        "edit_case_base.html", case_base_form=form, title="Create Case Base"
    )


@app.route("/case_base/<int:case_base_id>/edit", methods=["GET", "POST"])
def edit_case_base(case_base_id):
    form = CaseBaseForm()
    case_base = CaseBase.query.filter_by(id=case_base_id).first_or_404()
    if form.validate_on_submit():
        case_base.name = form.name.data
        case_base.description = form.description.data
        db.session.add(case_base)
        db.session.commit()
        flash("Case Base Updated")
        return redirect(url_for("index"))
    form.name.data = case_base.name
    form.description.data = case_base.description
    return render_template(
        "edit_case_base.html", case_base_form=form, title="Edit Case Base"
    )


@app.route("/case_base/<int:case_base_id>/delete", methods=["GET", "POST"])
def delete_case_base(case_base_id):
    case_base = CaseBase.query.filter_by(id=case_base_id).first_or_404()
    db.session.delete(case_base)
    db.session.commit()
    return redirect(url_for("index"))


### Cases
@app.route("/case_base/<int:case_base_id>/case/<int:case_id>")
def view_case(case_base_id, case_id):
    case = Case.query.filter_by(id=case_id).first_or_404()
    return render_template("case.html", case=case)


@app.route("/case_base/<int:case_base_id>/case/create", methods=["GET", "POST"])
def create_case(case_base_id):
    form = CaseForm()
    if form.validate_on_submit():
        case = Case(name=form.name.data, created_by="admin", case_base_id=case_base_id)
        db.session.add(case)
        db.session.commit()
        flash("Case Created")
        return redirect(url_for("view_case_base", case_base_id=case_base_id))
    return render_template(
        "edit_case.html", case_form=form, title="Create Case", case_base_id=case_base_id
    )


@app.route(
    "/case_base/<int:case_base_id>/case/<int:case_id>/edit", methods=["GET", "POST"]
)
def edit_case(case_base_id, case_id):
    form = CaseForm()
    case = Case.query.filter_by(id=case_id).first_or_404()

    if form.validate_on_submit():
        case.name = form.name.data
        db.session.add(case)
        db.session.commit()
        flash("Case Updated")
        return redirect(url_for("view_case_base", case_base_id=case_base_id))
    form.name.data = case.name
    return render_template(
        "edit_case.html", case_form=form, title="Edit Case", case_base_id=case_base_id
    )


@app.route(
    "/case_base/<int:case_base_id>/case/<int:case_id>/delete", methods=["GET", "POST"]
)
def delete_case(case_base_id, case_id):
    case = Case.query.filter_by(id=case_id).first_or_404()
    db.session.delete(case)
    db.session.commit()
    return redirect(url_for("view_case_base", case_base_id=case_base_id))


### Scenarios
@app.route("/scenario/<int:scenario_id>")
def view_scenario(scenario_id):
    scenario = Scenario.query.filter_by(id=scenario_id).first_or_404()
    return render_template("scenario.html", scenario=scenario)


@app.route(
    "/case_base/<int:case_base_id>/case/<int:case_id>/scenario/<int:scenario_id>"
)
def view_case_scenario(case_base_id, case_id, scenario_id):
    scenario = Scenario.query.filter_by(id=scenario_id).first_or_404()
    return render_template("scenario.html", scenario=scenario)


@app.route(
    "/case_base/<int:case_base_id>/case/<int:case_id>/scenario/create",
    methods=["GET", "POST"],
)
def create_case_scenario(case_base_id, case_id):
    form = ScenarioForm()
    if form.validate_on_submit():
        scenario = Scenario(name=form.name.data, created_by="admin", case_id=case_id)
        db.session.add(scenario)
        db.session.commit()
        flash("Scenario Created")
        return redirect(
            url_for("view_case", case_base_id=case_base_id, case_id=case_id)
        )
    return render_template(
        "edit_scenario.html",
        scenario_form=form,
        title="Create Scenario",
        case_base_id=case_base_id,
        case_id=case_id,
    )
