from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    TextAreaField,
    SelectField,
    IntegerField,
    RadioField,
)
from wtforms.validators import DataRequired


class ProbeForm(FlaskForm):
    type = SelectField(
        "Type",
        choices=["SelectTag", "SelectTreatment", "SelectCasualty"],
        default="MULTIPLECHOICE",
        description="Includes allowable values from the data source.",
    )
    probe_id = StringField("Probe ID")
    prompt = StringField("Prompt", validators=[DataRequired()])
    state = StringField("State")
    submit = SubmitField("Save Probe")


class ProbeOptionForm(FlaskForm):
    value = StringField("Value", validators=[DataRequired()])
    submit = SubmitField("Save Probe Option")


class ProbeResponseForm(FlaskForm):
    value = StringField("Value", default="NOVALUE")
    submit = SubmitField("Save Probe Response")


class ActionForm(FlaskForm):
    action_type = RadioField(
        "Action Type",
        choices=[
            ("APPLY_TREATMENT", "Apply Treatment"),
            ("CHECK_ALL_VITALS", "Check All Vitals"),
            ("CHECK_PULSE", "Check Pulse"),
            ("CHECK_RESPIRATION", "Check Respiration"),
            ("DIRECT_MOBILE_CASUALTIES", "Direct Mobile Casualties"),
            ("MOVE_TO_EVAC", "Move to Evac"),
            ("SITREP", "SITREP"),
            ("TAG_CASUALTY", "Tag Casualty"),
        ],
    )
    casualty = SelectField("Casualty", choices=[])
    treatment_type = SelectField(
        "Treatment Type",
        choices=[
            ("", ""),
            ("TOURNIQUET", "Tourniquet"),
            ("PRESSURE_BANDAGE", "Pressure bandage"),
            ("HEMOSTATIC_GAUZE", "Hemostatic gauze"),
            ("DECOMPRESSION_NEEDLE", "Decompression Needle"),
            ("NASOPHARYNGEAL_AIRWAY", "Nasopharyngeal airway"),
        ],
    )

    treatment_location = SelectField(
        "Location",
        choices=[
            ("", ""),
            ("UNSPECIFIED", "unspecified"),
            ("RIGHT_FOREARM", "right forearm"),
            ("LEFT_FOREARM", "left forearm"),
            ("RIGHT_CALF", "right calf"),
            ("LEFT_CALF", "left calf"),
            ("RIGHT_THIGH", "right thigh"),
            ("LEFT_THIGH", "left thigh"),
            ("RIGHT_STOMACH", "right stomach"),
            ("LEFT_STOMACH", "left stomach"),
            ("RIGHT_BICEP", "right bicep"),
            ("LEFT_BICEP", "left bicep"),
            ("RIGHT_SHOULDER", "right shoulder"),
            ("LEFT_SHOULDER", "left shoulder"),
            ("RIGHT_SIDE", "right side"),
            ("LEFT_SIDE", "left side"),
            ("RIGHT_CHEST", "right chest"),
            ("LEFT_CHEST", "left chest"),
            ("RIGT_WRIST", "right wrist"),
            ("LEFT_WRIST", "left wrist"),
            ("LEFT_FACE", "left face"),
            ("RIGHT_FACE", "right face"),
            ("LEFT_KNECK", "left neck"),
            ("RIGHT_NECK", "right neck"),
        ],
        description="Location of the injury.",
    )

    tag_label = SelectField(
        "Triage Category",
        choices=[
            ("", ""),
            ("MINIMAL", "MINIMAL (Green)"),
            ("DELAYED", "DELAYED (Yellow)"),
            ("IMMEDIATE", "IMMEDIATE (Red)"),
            ("EXPECTANT ", "EXPECTANT (Black)"),
        ],
    )
    submit = SubmitField("Save Action")
