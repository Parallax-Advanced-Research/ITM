from flask import render_template, redirect, flash, url_for
from app.scenario import scenario_blueprint as scenario
from app.scenario.forms import ScenarioForm, CasualtyForm, VitalsForm
from app.scenario.models import Scenario, Casualty, Vitals
from app.case.models import Case
from app import db


@scenario.route("/")
def index():
    return "Scenario"


#                             scenario
# add
@scenario.route("/add/<int:case_id>", methods=["GET", "POST"])
def add_scenario(case_id):
    scenario_form = ScenarioForm()
    if scenario_form.validate_on_submit():
        scenario = Scenario(
            description=scenario_form.description.data,
            mission_description=scenario_form.mission_description.data,
            mission_type=scenario_form.mission_type.data,
            threat_state_description=scenario_form.threat_state_description.data,
            created_by="admin",
        )
        case = Case.query.get_or_404(case_id)
        db.session.add(scenario)
        case.scenarios.append(scenario)
        db.session.commit()
        flash("Scenario added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "add_scenario.html",
        scenario_form=scenario_form,
        title="Add Scenario",
        case_id=case_id,
    )


# edit
@scenario.route("/edit/<int:scenario_id>", methods=["GET", "POST"])
def edit_scenario(scenario_id):
    scenario = Scenario.query.get_or_404(scenario_id)
    scenario_form = ScenarioForm(obj=scenario)
    case = scenario.cases[0]
    if scenario_form.validate_on_submit():
        scenario.description = scenario_form.description.data
        scenario.mission_description = scenario_form.mission_description.data
        scenario.mission_type = scenario_form.mission_type.data
        scenario.threat_state_description = scenario_form.threat_state_description.data
        db.session.add(scenario)
        db.session.commit()
        return redirect(url_for("case.view_case", case_id=case.id))
    return render_template(
        "edit_scenario.html",
        scenario_form=scenario_form,
        scenario=scenario,
        title="Edit Scenario for Case " + case.name,
        case=case,
    )


# delete
@scenario.route("/delete/<int:scenario_id>", methods=["GET", "POST"])
def delete_scenario(scenario_id):
    scenario = Scenario.query.get_or_404(scenario_id)
    case_id = scenario.cases[0].id
    db.session.delete(scenario)
    db.session.commit()
    flash("Scenario deleted successfully.")
    return redirect(url_for("case.view_case", case_id=case_id))


#                             casualty
# add
@scenario.route("/casualty/add/<int:scenario_id>", methods=["GET", "POST"])
def add_casualty(scenario_id):
    casualty_form = CasualtyForm()
    scenario = Scenario.query.get_or_404(scenario_id)
    case_id = scenario.cases[0].id
    if casualty_form.validate_on_submit():
        casualty = Casualty(
            name=casualty_form.name.data,
            description=casualty_form.description.data,
            age=casualty_form.age.data,
            sex=casualty_form.sex.data,
            rank=casualty_form.rank.data,
            relationship_type=casualty_form.relationship_type.data,
        )
        db.session.add(casualty)
        scenario.casualties.append(casualty)
        db.session.commit()
        flash("Casualty added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "add_casualty.html",
        casualty_form=casualty_form,
        title="Add Casualty",
        scenario_id=scenario_id,
    )


# edit
@scenario.route("/casualty/edit/<int:casualty_id>", methods=["GET", "POST"])
def edit_casualty(casualty_id):
    casualty = Casualty.query.get_or_404(casualty_id)
    scenario = casualty.scenarios[0]
    scenario_id = scenario.id
    case_id = scenario.cases[0].id
    casualty_form = CasualtyForm(obj=casualty)
    if casualty_form.validate_on_submit():
        casualty.name = casualty_form.name.data
        casualty.description = casualty_form.description.data
        casualty.age = casualty_form.age.data
        casualty.sex = casualty_form.sex.data
        casualty.rank = casualty_form.rank.data
        casualty.relationship_type = casualty_form.relationship_type.data
        db.session.add(casualty)
        db.session.commit()
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "add_casualty.html",
        casualty_form=casualty_form,
        casualty=casualty,
        title="Edit Casualty",
        scenario_id=scenario_id,
    )


# delete
@scenario.route("/casualty/delete/<int:casualty_id>", methods=["GET", "POST"])
def delete_casualty(casualty_id):
    casualty = Casualty.query.get_or_404(casualty_id)
    scenario = casualty.scenarios[0]
    case_id = scenario.cases[0].id
    db.session.delete(casualty)
    db.session.commit()
    flash("Casualty deleted successfully.")
    return redirect(url_for("case.view_case", case_id=case_id))


#                             vitals
# add
@scenario.route("/vitals/add/<int:casualty_id>", methods=["GET", "POST"])
def add_vitals(casualty_id):
    vitals_form = VitalsForm()
    casualty = Casualty.query.get_or_404(casualty_id)
    scenario_id = casualty.scenarios[0].id
    case_id = casualty.scenarios[0].cases[0].id
    if vitals_form.validate_on_submit():
        vitals = Vitals(
            heart_rate=vitals_form.heart_rate.data,
            blood_pressure=vitals_form.blood_pressure.data,
            oxygen_saturation=vitals_form.oxygen_saturation.data,
            respiratory_rate=vitals_form.respiratory_rate.data,
            pain=vitals_form.pain.data,
            mental_status=vitals_form.mental_status.data,
            concious=vitals_form.concious.data,
        )
        db.session.add(vitals)
        casualty.vitals.append(vitals)
        db.session.commit()
        flash("Vitals added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "add_vitals.html",
        vitals_form=vitals_form,
        title="Add Vitals",
        casualty_id=casualty_id,
    )


# edit
@scenario.route("/vitals/edit/<int:vitals_id>", methods=["GET", "POST"])
def edit_vitals(vitals_id):
    vitals = Vitals.query.get_or_404(vitals_id)
    casualty = vitals.casualty[0]
    vitals_form = VitalsForm(obj=vitals)
    case_id = casualty.scenarios[0].cases[0].id
    if vitals_form.validate_on_submit():
        vitals = Vitals(
            heart_rate=vitals_form.heart_rate.data,
            blood_pressure=vitals_form.blood_pressure.data,
            oxygen_saturation=vitals_form.oxygen_saturation.data,
            respiratory_rate=vitals_form.respiratory_rate.data,
            pain=vitals_form.pain.data,
            mental_status=vitals_form.mental_status.data,
            concious=vitals_form.concious.data,
        )
        db.session.add(vitals)
        casualty.vitals.append(vitals)
        db.session.commit()
        flash("Vitals added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "add_vitals.html",
        vitals_form=vitals_form,
        title="Edit Vitals",
        casualty_id=casualty.id,
    )


# delete
@scenario.route("/vitals/delete/<int:vitals_id>", methods=["GET", "POST"])
def delete_vitals(vitals_id):
    vitals = Vitals.query.get_or_404(vitals_id)
    casualty = vitals.casualty[0]
    case_id = casualty.scenarios[0].cases[0].id
    db.session.delete(vitals)
    db.session.commit()
    flash("Vitals deleted successfully.")
    return redirect(url_for("case.view_case", case_id=case_id))
