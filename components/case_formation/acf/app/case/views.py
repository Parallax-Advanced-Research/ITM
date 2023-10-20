from flask import render_template, redirect, url_for, flash, request
from app.case import case_blueprint as case
from app.case.forms import CaseForm
from app.case.models import Case
from app import db


@case.route("/")
def index():
    return redirect(url_for("main.view_casebase_list"))


#                             case
# add
@case.route("/add/casebase/<int:casebase_id>", methods=["GET", "POST"])
def add_case(casebase_id):
    if casebase_id is None:
        flash("Please select a casebase to add a case.")
        return redirect(url_for("main.view_casebase_list"))
    case_form = CaseForm()
    if case_form.validate_on_submit():
        case = Case(
            external_id=case_form.external_id.data,
            name=case_form.name.data,
            casebase_id=casebase_id,
            created_by="admin",
        )
        db.session.add(case)
        db.session.commit()
        flash("Case added successfully.")
        return redirect(url_for("case.view_case", case_id=case.id))
    return render_template("add_case.html", case_form=case_form, title="Add Case")


# edit
@case.route("/edit/<int:case_id>", methods=["GET", "POST"])
def edit_case(case_id):
    case = Case.query.get_or_404(case_id)
    case_form = CaseForm(obj=case)
    if case_form.validate_on_submit():
        case.external_id = case_form.external_id.data
        case.name = case_form.name.data
        db.session.add(case)
        db.session.commit()
        return redirect(url_for("main.view_casebase", casebase_id=case.casebase_id))
    return render_template(
        "edit_case.html", case_form=case_form, case=case, title="Edit Case"
    )


# delete
@case.route("/delete/<int:case_id>", methods=["GET", "POST"])
def delete_case(case_id):
    case = Case.query.get_or_404(case_id)
    casebase_id = case.casebase_id
    db.session.delete(case)
    db.session.commit()
    flash("Case deleted successfully.")
    return redirect(url_for("main.view_casebase", casebase_id=casebase_id))


# view
@case.route("/<int:case_id>")
def view_case(case_id):
    case = Case.query.get_or_404(case_id)
    return render_template("view_case.html", case=case, title=case.name)
