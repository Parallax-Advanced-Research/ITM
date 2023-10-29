from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class CaseBaseForm(FlaskForm):
    name = StringField(
        "Case Base Name",
        validators=[DataRequired()],
        description="Unique string to name this case base.",
    )
    description = TextAreaField(
        "Description",
        description="Description of this case base.",
    )
    submit = SubmitField("Save")


class CaseForm(FlaskForm):
    name = StringField(
        "Case Name",
        validators=[DataRequired()],
        description="Unique string to name this case",
    )
    submit = SubmitField("Save")
