from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField, IntegerField
from wtforms.validators import NumberRange


class ScenarioForm(FlaskForm):
    description = TextAreaField(
        "Description",
        description="Description of this scenario, maps to unstructured input field.",
    )
    mission_description = TextAreaField(
        "Mission Description",
        description="Maps to unstructured input field.",
    )
    mission_type = SelectField(
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
        description="Includes allowable values from the data source.",
    )
    threat_state_description = TextAreaField("Threat State Description")
    submit = SubmitField("Save Scenario")


class CasualtyForm(FlaskForm):
    name = StringField("Name", description="Casualty name.")
    description = TextAreaField(
        "Description", description="Maps to casualty unstructured field."
    )
    age = IntegerField(
        "Age",
        validators=[NumberRange(min=0, max=120)],
        default=0,
        description="Age in (int) years.",
    )
    sex = SelectField("Sex", choices=[("", ""), ("M", "M"), ("F", "F")])
    rank = SelectField(
        "Rank",
        choices=[
            ("", ""),
            ("CIVILIAN", "Civilian"),
            ("MILITARY", "Military"),
            ("VIP", "VIP"),
        ],
        description="Individual's rank or importance to a given mission.",
    )
    relationship_type = SelectField(
        "Relationship Type",
        choices=[
            ("", ""),
            ("NONE", "NONE"),
            ("FRIEND", "FRIEND"),
            ("ENEMY", "ENEMY"),
        ],
        description="Relationship to the casualty.",
    )
    submit = SubmitField("Save Casualty")


class VitalsForm(FlaskForm):
    heart_rate = IntegerField(
        "Heart Rate",
        validators=[NumberRange(min=0)],
        description="Heart rate in beats per minute.",
        default=0,
    )
    blood_pressure = IntegerField(
        "Blood Pressure",
        validators=[NumberRange(min=0)],
        description="Blood pressure in mmHg.",
        default=0,
    )
    oxygen_saturation = IntegerField(
        "Oxygen Saturation",
        validators=[NumberRange(min=0, max=100)],
        description="Oxygen saturation in percent.",
        default=0,
    )
    respiratory_rate = IntegerField(
        "Respiratory Rate",
        description="Respiratory rate in breaths per minute.",
        default=0,
    )
    pain = IntegerField(
        "Pain",
        validators=[NumberRange(min=0, max=10)],
        description="Pain level on a scale of 0-10.",
        default=0,
    )
    mental_status = SelectField(
        "Mental Status",
        choices=[
            # ("A", "A"),
            # ("V", "V"),
            # ("P", "P"),
            # ("U", "U"),
            ("", ""),
            ("UNRESPONSIVE", "UNRESPONSIVE"),
            ("CONFUSED", "CONFUSED"),
            ("NORMAL", "NORMAL"),
        ],
        description="Mental status. Should be A V P U",
    )
    concious = SelectField(
        "Concious",
        choices=[
            ("", ""),
            ("CONCIOUS", True),
            ("UNCONCIOUS", False),
        ],
        description="Conciousness status.",
    )
    submit = SubmitField("Save Vitals")
