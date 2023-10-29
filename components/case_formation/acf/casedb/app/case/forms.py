from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length


class CaseBaseForm(FlaskForm):
    name = StringField(
        "Case Base Name",
        validators=[DataRequired()],
        description="Unique string to name this case base",
    )
    description = TextAreaField(
        "Description",
        description="Description of this case base",
    )
    submit = SubmitField("Save")


class CaseForm(FlaskForm):
    name = StringField(
        "Case Name",
        validators=[DataRequired()],
        description="Unique string to name this case",
    )
    external_id = StringField(
        "External ID",
        description="The id, if any from the data source.",
    )

    submit = SubmitField("Save")


class FullCaseForm:
    name = StringField(
        "Case Name",
        validators=[DataRequired()],
        description="Unique string to name this case",
    )
    external_id = StringField(
        "External ID",
        description="The id, if any from the data source.",
    )
    eval_mission_type = SelectField(
        "Mission Type",
        choices=[
            ("", ""),
            ("OTHER", "Other"),
            ("DELIVERCARGO", "DeliverCargo"),
            ("DEFENDBASE", "DefendBase"),
            ("PROTECTCIVILIANS", "ProtectCivilians"),
            ("PROTECTMVP", "ProtectMVP"),
            ("SECURITYPATROL", "SecurityPatrol"),
        ],
        default="",
        description="Includes allowable values from the data source (TA1 Mission types).",
    )
    threat_state_description = TextAreaField("Threat State Description")
    submit = SubmitField("Save Scenario")
