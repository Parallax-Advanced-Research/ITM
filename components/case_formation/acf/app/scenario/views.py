from flask import render_template, redirect, flash, url_for
from app.scenario import scenario_blueprint as scenario
from app.scenario.forms import (
    ScenarioForm,
    CasualtyForm,
    VitalsForm,
    InjuryForm,
    SupplyForm,
    ThreatForm,
    EnvironmentForm,
)
from app.scenario.models import (
    Scenario,
    Casualty,
    Vitals,
    Injury,
    Supply,
    Threat,
    Environment,
)
from app.case.models import Case, MissionType, SupplyTypes, RelationshipTypes, RankTypes
from app import db


@scenario.app_template_filter("validate_api_member")
def validate_api_member_filter(api_member):
    """a generic version of the below filters, which can be used for any enum"""
    pass


@scenario.app_template_filter("validate_mission_type")
def validate_mission_type_filter(mission_type):
    if mission_type in MissionType.__members__:
        mission_type = MissionType.get_member(mission_type).value
        return '<span class="text-success fw-bold">{}</span>'.format(mission_type)
    else:
        return '<span class="text-danger fw-bold">{}</span>'.format(mission_type)


@scenario.app_template_filter("validate_supply_type")
def validate_supply_type_filter(supply_type):
    if supply_type in SupplyTypes.__members__:
        supply_type = SupplyTypes.get_member(supply_type).value
        return '<span class="text-success">{}</span>'.format(supply_type)
    else:
        return '<span class="text-danger fw-bold">{}</span>'.format(supply_type)


@scenario.app_template_filter("validate_relationship_type")
def validate_relationship_type_filter(relationship_type):
    if relationship_type in RelationshipTypes.__members__:
        relationship_type = RelationshipTypes.get_member(relationship_type).value
        return '<span class="text-success">{}</span>'.format(relationship_type)
    else:
        return '<span class="text-danger fw-bold">{}</span>'.format(relationship_type)


@scenario.app_template_filter("validate_rank_type")
def validate_rank_type_filter(rank_type):
    if rank_type in RelationshipTypes.__members__:
        rank_type = RelationshipTypes.get_member(rank_type).value
        return '<span class="text-success">{}</span>'.format(rank_type)
    else:
        return '<span class="text-danger fw-bold">{}</span>'.format(rank_type)


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
            elapsed_time=scenario_form.elapsed_time.data,
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
        scenario.mission_type = (
            scenario_form.eval_mission_type.data
            if scenario_form.eval_mission_type.data
            else scenario_form.mission_type.data
        )
        scenario.threat_state_description = scenario_form.threat_state_description.data
        scenario.elapsed_time = scenario_form.elapsed_time.data
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
            triage_criteria=casualty_form.triage_criteria.data,
            triage_description=casualty_form.triage_description.data,
            tag_label=casualty_form.tag_label.data,
            created_by="admin",
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
        casualty.triage_criteria = casualty_form.triage_criteria.data
        casualty.triage_description = casualty_form.triage_description.data
        casualty.tag_label = casualty_form.tag_label.data
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
            created_by="admin",
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
        vitals.heart_rate = vitals_form.heart_rate.data
        vitals.blood_pressure = vitals_form.blood_pressure.data
        vitals.oxygen_saturation = vitals_form.oxygen_saturation.data
        vitals.respiratory_rate = vitals_form.respiratory_rate.data
        vitals.pain = vitals_form.pain.data
        vitals.mental_status = vitals_form.mental_status.data
        vitals.concious = vitals_form.concious.data
        db.session.add(vitals)
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


#                             injury
# add
@scenario.route("/injury/add/<int:casualty_id>", methods=["GET", "POST"])
def add_injury(casualty_id):
    injury_form = InjuryForm()
    casualty = Casualty.query.get_or_404(casualty_id)
    scenario_id = casualty.scenarios[0].id
    case_id = casualty.scenarios[0].cases[0].id
    if injury_form.validate_on_submit():
        injury = Injury(
            injury_type=injury_form.injury_type.data,
            injury_severity=injury_form.injury_severity.data,
            injury_location=injury_form.injury_location.data,
            created_by="admin",
        )
        db.session.add(injury)
        casualty.injuries.append(injury)
        db.session.commit()
        flash("Injury added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "add_injury.html",
        injury_form=injury_form,
        title="Add Injury",
        casualty_id=casualty_id,
    )


# edit
@scenario.route("/injury/edit/<int:injury_id>", methods=["GET", "POST"])
def edit_injury(injury_id):
    injury = Injury.query.get_or_404(injury_id)
    casualty = injury.casualty
    injury_form = InjuryForm(obj=injury)
    case_id = casualty.scenarios[0].cases[0].id
    if injury_form.validate_on_submit():
        injury.injury_type = injury_form.injury_type.data
        injury.injury_severity = injury_form.injury_severity.data
        injury.injury_location = injury_form.injury_location.data
        db.session.add(injury)
        db.session.commit()
        flash("Injury added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "add_injury.html",
        injury_form=injury_form,
        title="Edit Injury",
        casualty_id=casualty.id,
    )


# delete
@scenario.route("/injury/delete/<int:injury_id>", methods=["GET", "POST"])
def delete_injury(injury_id):
    injury = Injury.query.get_or_404(injury_id)
    casualty = injury.casualty
    case_id = casualty.scenarios[0].cases[0].id
    db.session.delete(injury)
    db.session.commit()
    flash("Injury deleted successfully.")
    return redirect(url_for("case.view_case", case_id=case_id))


#                             supply
# add
@scenario.route("/supply/add/<int:scenario_id>", methods=["GET", "POST"])
def add_supply(scenario_id):
    supply_form = SupplyForm()
    scenario = Scenario.query.get_or_404(scenario_id)
    case_id = scenario.cases[0].id
    if supply_form.validate_on_submit():
        supply = Supply(
            supply_type=supply_form.supply_type.data,
            supply_quantity=supply_form.supply_quantity.data,
            created_by="admin",
        )
        db.session.add(supply)
        scenario.supplies.append(supply)
        db.session.commit()
        flash("Supply added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "add_supply.html",
        supply_form=supply_form,
        title="Add Supply",
        scenario_id=scenario_id,
    )


# edit
@scenario.route("/supply/edit/<int:supply_id>", methods=["GET", "POST"])
def edit_supply(supply_id):
    supply = Supply.query.get_or_404(supply_id)
    scenario = supply.scenario
    supply_form = SupplyForm(obj=supply)
    case_id = scenario.cases[0].id
    if supply_form.validate_on_submit():
        supply.supply_type = supply_form.supply_type.data
        supply.supply_quantity = supply_form.supply_quantity.data
        db.session.add(supply)
        db.session.commit()
        flash("Supply added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "edit_supply.html",
        supply=supply,
        supply_form=supply_form,
        title="Edit Supply",
        scenario_id=scenario.id,
    )


# delete
@scenario.route("/supply/delete/<int:supply_id>", methods=["GET", "POST"])
def delete_supply(supply_id):
    supply = Supply.query.get_or_404(supply_id)
    scenario = supply.scenario
    case_id = scenario.cases[0].id
    db.session.delete(supply)
    db.session.commit()
    flash("Supply deleted successfully.")
    return redirect(url_for("case.view_case", case_id=case_id))


#                             threat
# add
@scenario.route("/threat/add/<int:scenario_id>", methods=["GET", "POST"])
def add_threat(scenario_id):
    scenario = Scenario.query.get_or_404(scenario_id)
    case_id = scenario.cases[0].id
    threat_form = ThreatForm()
    if threat_form.validate_on_submit():
        threat = Threat(
            threat_type=threat_form.threat_type.data,
            threat_severity=threat_form.threat_severity.data,
            created_by="admin",
        )
        db.session.add(threat)
        scenario.threats.append(threat)
        db.session.commit()
        flash("Threat added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "add_threat.html",
        threat_form=threat_form,
        title="Add Threat",
        scenario_id=scenario_id,
    )


# delete
@scenario.route("/threat/delete/<int:threat_id>", methods=["GET", "POST"])
def delete_threat(threat_id):
    threat = Threat.query.get_or_404(threat_id)
    scenario = threat.scenario
    case_id = scenario.cases[0].id
    db.session.delete(threat)
    db.session.commit()
    flash("Threat deleted successfully.")
    return redirect(url_for("case.view_case", case_id=case_id))


#                             environment
# add
@scenario.route("/environment/add/<int:scenario_id>", methods=["GET", "POST"])
def add_environment(scenario_id):
    scenario = Scenario.query.get_or_404(scenario_id)
    case_id = scenario.cases[0].id
    environment_form = EnvironmentForm()
    if environment_form.validate_on_submit():
        environment = Environment(
            aid_delay=environment_form.aid_delay.data,
            fauna=environment_form.fauna.data,
            flora=environment_form.flora.data,
            humidity=environment_form.humidity.data,
            lighting=environment_form.lighting.data,
            location=environment_form.location.data,
            noise_ambient=environment_form.noise_ambient.data,
            noise_peak=environment_form.noise_peak.data,
            soundscape=environment_form.soundscape.data,
            temperature=environment_form.temperature.data,
            terrain=environment_form.terrain.data,
            unstructured=environment_form.unstructured.data,
            visibility=environment_form.visibility.data,
            weather=environment_form.weather.data,
            created_by="admin",
            scenario_id=scenario.id,
        )
        db.session.add(environment)
        scenario.environment.append(environment)
        db.session.commit()
        flash("Environment added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "add_environment.html",
        environment_form=environment_form,
        title="Add Environment",
        scenario_id=scenario_id,
    )


# edit
@scenario.route("/environment/edit/<int:scenario_id>", methods=["GET", "POST"])
def edit_environment(scenario_id):
    scenario = Scenario.query.get_or_404(scenario_id)
    environment_id = scenario.environment[0].id
    environment = Environment.query.get_or_404(environment_id)
    scenario = environment.scenario
    case_id = scenario.cases[0].id
    environment_form = EnvironmentForm(obj=environment)
    if environment_form.validate_on_submit():
        environment.aid_delay = environment_form.aid_delay.data
        environment.fauna = environment_form.fauna.data
        environment.flora = environment_form.flora.data
        environment.humidity = environment_form.humidity.data
        environment.lighting = environment_form.lighting.data
        environment.location = environment_form.location.data
        environment.noise_ambient = environment_form.noise_ambient.data
        environment.noise_peak = environment_form.noise_peak.data
        environment.soundscape = environment_form.soundscape.data
        environment.temperature = environment_form.temperature.data
        environment.terrain = environment_form.terrain.data
        environment.unstructured = environment_form.unstructured.data
        environment.visibility = environment_form.visibility.data
        environment.weather = environment_form.weather.data
        db.session.add(environment)
        db.session.commit()
        flash("Environment added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "edit_environment.html",
        environment=environment,
        environment_form=environment_form,
        title="Edit Environment",
        scenario_id=scenario.id,
    )


# delete
@scenario.route("/environment/delete/<int:scenario_id>", methods=["GET", "POST"])
def delete_environment(scenario_id):
    scenario = Scenario.query.get_or_404(scenario_id)
    environment_id = scenario.environment[0].id
    environment = Environment.query.get_or_404(environment_id)
    case_id = scenario.cases[0].id
    db.session.delete(environment)
    db.session.commit()
    flash("Environment deleted successfully.")
    return redirect(url_for("case.view_case", case_id=case_id))
