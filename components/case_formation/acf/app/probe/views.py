from flask import render_template, redirect, flash, url_for
from app.probe import probe_blueprint as probe
from app.probe.forms import ProbeForm, ProbeOptionForm, ProbeResponseForm
from app.probe.models import Probe, ProbeOption, ProbeResponse
from app.scenario.models import Scenario
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
