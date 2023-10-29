from app.main import main_blueprint as main
from flask import render_template, redirect, url_for, flash, request
from app.case.forms import CaseBaseForm
from app.case.models import CaseBase
from app import db


@main.route("/")
def index():
    return redirect(url_for("main.view_casebase_list"))


#                             case base
# list
@main.route("/casebases")
@main.route("/casebase/list")
def view_casebase_list():
    casebase_list = CaseBase.query.all()
    return render_template(
        "view_casebase_list.html", casebase_list=casebase_list, title="Case Base List"
    )


# add
@main.route("/casebase/add", methods=["GET", "POST"])
def add_casebase():
    casebase_form = CaseBaseForm()
    if casebase_form.validate_on_submit():
        casebase = CaseBase(
            name=casebase_form.name.data,
            description=casebase_form.description.data,
        )
        db.session.add(casebase)
        db.session.commit()
        flash("Case base added successfully.")
        return redirect(url_for("main.view_casebase_list"))
    return render_template(
        "add_casebase.html", casebase_form=casebase_form, title="Add Case Base"
    )


# view
@main.route("/casebase/<int:casebase_id>")
def view_casebase(casebase_id):
    casebase = CaseBase.query.get_or_404(casebase_id)
    cases = casebase.cases.all()
    return render_template(
        "view_casebase.html", casebase=casebase, cases=cases, title=casebase.name
    )


# edit
@main.route("/casebase/<int:casebase_id>/edit", methods=["GET", "POST"])
def edit_casebase(casebase_id):
    casebase_form = CaseBaseForm()
    casebase = CaseBase.query.get_or_404(casebase_id)
    if casebase_form.validate_on_submit():
        casebase.name = casebase_form.name.data
        casebase.description = casebase_form.description.data
        db.session.add(casebase)
        db.session.commit()
        flash("Case base updated successfully.")
        return redirect(url_for("main.view_casebase_list"))
    elif request.method == "GET":
        casebase_form.name.data = casebase.name
        casebase_form.description.data = casebase.description
    return render_template(
        "edit_casebase.html", casebase_form=casebase_form, casebase_id=casebase.id
    )


# delete
@main.route("/casebase/<int:casebase_id>/delete", methods=["GET", "POST"])
def delete_casebase(casebase_id):
    casebase = CaseBase.query.get_or_404(casebase_id)
    db.session.delete(casebase)
    db.session.commit()
    flash("Case base deleted successfully.")
    return redirect(url_for("main.view_casebase_list"))
