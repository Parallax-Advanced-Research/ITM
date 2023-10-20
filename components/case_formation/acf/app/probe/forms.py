from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired


class ProbeForm(FlaskForm):
    type = SelectField(
        "Type",
        choices=[
            ("", ""),
            ("MULTIPLECHOICE", "MultipleChoice"),
            ("FREERESPONSE", "FreeResponse"),
            ("PATIENTORDERING", "PatientOrdering"),
        ],
        default="MULTIPLECHOICE",
        description="Includes allowable values from the data source.",
    )
    prompt = StringField("Prompt", validators=[DataRequired()])
    state = StringField("State")
    submit = SubmitField("Save Probe")


class ProbeOptionForm(FlaskForm):
    value = StringField("Value", validators=[DataRequired()])
    submit = SubmitField("Save Probe Option")


class ProbeResponseForm(FlaskForm):
    value = StringField("Value", default="NOVALUE")
    submit = SubmitField("Save Probe Response")
