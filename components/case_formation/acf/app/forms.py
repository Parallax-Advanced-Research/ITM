from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField, BooleanField
from wtforms.validators import DataRequired, ValidationError, Length


class CaseBaseForm(FlaskForm):
    name = StringField(
        "Case Base Name",
        validators=[DataRequired()],
        description="Unique string to name this case base",
    )
    description = TextAreaField(
        "Description",
        validators=[Length(min=0, max=255)],
        description="Description of this case base",
    )
    submit = SubmitField("Save")


class CaseForm(FlaskForm):
    name = StringField(
        "Case Name",
        validators=[DataRequired()],
        description="Unique string to name this case",
    )
    submit = SubmitField("Save")


class ScenarioForm(FlaskForm):
    name = StringField(
        "Scenario Name",
        validators=[DataRequired()],
        description="Unique string to name this scenario",
    )
    submit = SubmitField("Save")
