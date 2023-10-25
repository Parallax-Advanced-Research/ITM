from flask import render_template, redirect, flash, url_for
from app.probe import probe_blueprint as probe
from app.probe.forms import ProbeForm, ProbeOptionForm, ProbeResponseForm, ActionForm
from app.probe.models import Probe, ProbeOption, ProbeResponse, Action, ActionParameters
from app.scenario.models import Scenario, Threat, Casualty
from app import db


@probe.route("/")
def index():
    return "Probe"


#                             probes
# add
@probe.route("/add/<int:scenario_id>", methods=["GET", "POST"])
def add_probe(scenario_id):
    scenario = Scenario.query.get_or_404(scenario_id)
    case_id = scenario.cases[0].id
    probe_form = ProbeForm()
    if probe_form.validate_on_submit():
        probe = Probe(
            type=probe_form.type.data,
            prompt=probe_form.prompt.data,
            created_by="admin",
        )
        db.session.add(probe)
        scenario.probes.append(probe)
        db.session.commit()
        flash("Probe added successfully.")
        return redirect(url_for("probe.edit_probe", probe_id=probe.id, case_id=case_id))
    return render_template(
        "add_probe.html",
        probe_form=probe_form,
        title="Add Probe",
        scenario_id=scenario_id,
        case_id=case_id,
    )


# edit
@probe.route("/edit/<int:probe_id>", methods=["GET", "POST"])
def edit_probe(probe_id):
    probe = Probe.query.get_or_404(probe_id)
    case_id = probe.scenario.cases[0].id
    probe_form = ProbeForm(obj=probe)
    if probe_form.validate_on_submit():
        probe.type = probe_form.type.data
        probe.prompt = probe_form.prompt.data
        db.session.commit()
        flash("Probe updated successfully.")
        return redirect(url_for("probe.edit_probe", probe_id=probe.id))
    return render_template(
        "add_probe.html",
        probe_form=probe_form,
        title="Edit Probe",
        probe=probe,
        case_id=case_id,
    )


# delete
@probe.route("/delete/<int:probe_id>", methods=["GET", "POST"])
def delete_probe(probe_id):
    probe = Probe.query.get_or_404(probe_id)
    case_id = probe.scenario.cases[0].id
    db.session.delete(probe)
    db.session.commit()
    flash("Probe deleted successfully.")
    return redirect(url_for("case.view_case", case_id=case_id))


#                             options
# add
@probe.route("/add/options/<int:probe_id>", methods=["GET", "POST"])
def add_probe_option(probe_id):
    probe_option_form = ProbeOptionForm()
    if probe_option_form.validate_on_submit():
        probe_option = ProbeOption(
            value=probe_option_form.value.data,
            created_by="admin",
        )
        probe = Probe.query.get_or_404(probe_id)
        db.session.add(probe_option)
        probe.options.append(probe_option)
        db.session.commit()
        flash("Probe Option added successfully.")
        return redirect(url_for("probe.edit_probe", probe_id=probe.id))
    return render_template(
        "add_probe_option.html",
        probe_option_form=probe_option_form,
        title="Add Probe Option",
        probe_id=probe_id,
    )


# delete
@probe.route("/delete/options/<int:probe_option_id>", methods=["GET", "POST"])
def delete_probe_option(probe_option_id):
    probe_option = ProbeOption.query.get_or_404(probe_option_id)
    probe_id = probe_option.probe.id
    db.session.delete(probe_option)
    db.session.commit()
    flash("Probe Option deleted successfully.")
    return redirect(url_for("probe.edit_probe", probe_id=probe_id))


#                             action
# add
@probe.route("/add/action/<int:response_id>", methods=["GET", "POST"])
def add_action(response_id):
    response = ProbeResponse.query.get_or_404(response_id)
    probe = response.probe
    scenario = probe.scenario
    case_id = scenario.cases[0].id
    casualty_choices = scenario.casualties
    action_form = ActionForm()
    action_form.casualty.choices = [
        (casualty.name, casualty.name) for casualty in casualty_choices
    ]

    if action_form.validate_on_submit():
        casualty = Casualty.query.filter_by(name=action_form.casualty.data).first()
        action = Action(
            action_type=action_form.action_type.data,
            created_by="import",
        )
        db.session.add(action)

        if action_form.action_type.data == "APPLY_TREATMENT":
            action.apply_treatment(action_form.treatment_type.data)

        if action_form.action_type.data == "TAG_CASUALTY":
            action.tag_casualty(action_form.tag_label.data)
            # casualty.tag_label = action_form.tag_label.data

        if action_form.treatment_location != "":
            action_parameter = ActionParameters(
                parameter_type="location",
                parameter_value=action_form.treatment_location.data,
            )
            action.parameters.append(action_parameter)
            db.session.add(action_parameter)

        casualty.actions.append(action)
        casualty.save()

        response.actions.append(action)
        db.session.commit()
        flash("Action added successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))

    return render_template(
        "add_action.html",
        response=response,
        action_form=action_form,
        title="Add Action",
    )


# delete
@probe.route("/delete/action/<int:action_id>", methods=["GET", "POST"])
def delete_action(action_id):
    action = Action.query.get_or_404(action_id)
    casualty = action.casualty
    case_id = action.probe_response.probe.scenario.cases[0].id
    casualty.actions.remove(action)
    db.session.delete(action)
    db.session.commit()
    flash("Action deleted successfully.")
    return redirect(url_for("case.view_case", case_id=case_id))


# edit
"""
@probe.route("/edit/action/<int:action_id>", methods=["GET", "POST"])
def edit_action(action_id):
    action = Action.query.get_or_404(action_id)
    response = action.probe_response
    case_id = action.probe_response.probe.scenario.cases[0].id
    action_form = ActionForm(obj=action)
    casualties = action.probe_response.probe.scenario.casualties
    parameters = action.parameters
    # if there is a treatment parameter already set, set the treatment_type
    treatment_type = ""
    for parameter in parameters:
        if parameter.parameter_type == "treatment":
            treatment_type = parameter.parameter_value
    action_form.treatment_type.data = treatment_type

    action_form.casualty.choices = [
        (casualty.name, casualty.name) for casualty in casualties
    ]

    if action_form.validate_on_submit():
        if (
            action_form.action_type.data == "APPLY_TREATMENT"
            and action_form.treatment_type != treatment_type
        ):
            action_parameter = ActionParameters(
                parameter_type="treatment",
                parameter_value=action_form.treatment_type.data,
                created_by="import",
            )
            action.parameters.append(action_parameter)
            db.session.add(action_parameter)

        action.action_type = action_form.action_type.data
        action.casualty = action_form.casualty.data
        db.session.commit()
        flash("Action updated successfully.")
        return redirect(url_for("case.view_case", case_id=case_id))
    return render_template(
        "add_action.html",
        response=response,
        action_form=action_form,
        title="Edit Action",
        action=action,
    )
"""
