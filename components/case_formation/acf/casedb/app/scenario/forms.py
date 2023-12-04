from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    TextAreaField,
    SelectField,
    IntegerField,
    FloatField,
)
from wtforms.validators import NumberRange, DataRequired


class ScenarioForm(FlaskForm):
    description = TextAreaField(
        "Description",
        description="Description of this scenario, maps to unstructured Sate evaluation field.",
    )
    mission_description = TextAreaField(
        "Mission Description",
        description="Maps to unstructured state input field.",
    )
    eval_mission_type = SelectField(
        "Eval Mission Type",
        choices=[
            ("", ""),
            ("LISTENING_OBSERVATION", "Listening/Observation"),
            ("DIRCT_ACTION", "Direct Action"),
            ("HOSTAGE_RESCUE", "Hostage rescue"),
            ("ASSET_TRANSPORT", "Asset transport"),
            ("SENSOR_EMPLACEMENT", "Sensor emplacement"),
            ("INTELLIGENCE_GATHERING", "Intelligence gathering"),
            ("CIVIL_AFFAIRS", "Civil affairs"),
            ("TRAINING", "Training"),
            ("SABOTAGE", "Sabotage"),
            ("SECURITY_PATROL", "Security patrol"),
            ("FIRE_SUPPORT", "Fire support"),
            ("NUCLEAR_DETERRENCE", "Nuclear deterrence"),
            ("EXTRACTION", "Extraction"),
            ("UNKNOWN", "Unknown"),
        ],
        default="",
        description="Includes allowable values from the evaluation api (TA3 Mission types).",
    )
    mission_type = StringField(
        "Mission Type",
        description="Mission type from the data source (TA1 Mission types).",
    )
    threat_state_description = TextAreaField(
        "Threat State Description", description="Text description of current threats."
    )
    elapsed_time = StringField("Elapsed Time", description="Elapsed time in minutes.")
    submit = SubmitField("Save Scenario")


class CasualtyForm(FlaskForm):
    name = StringField("Name", description="Casualty name.")
    description = TextAreaField(
        "Description", description="Maps to casualty unstructured field."
    )
    age = StringField(
        "Age",
        description="Age in (int) years.",
    )
    sex = SelectField("Sex", choices=[("", ""), ("M", "M"), ("F", "F")])
    rank = SelectField(
        "Rank",
        choices=[
            ("", ""),
            ("MARINE", "Marine"),
            ("FMF_CORPSMAN", "FMF Corpsman"),
            ("SAILOR", "Sailor"),
            ("Civilian", "Civilian"),
            ("SEAL", "SEAL"),
            ("INTEL_OFFICER", "Intel Officer"),
        ],
        description="Individual's rank or importance to a given mission.",
    )
    relationship_type = SelectField(
        "Relationship Type",
        choices=[
            ("", ""),
            ("NONE", "None"),
            ("ALLY", "Ally"),
            ("FRIEND", "Friend"),
            ("HOSTILE", "Hostile"),
            ("EXPECTANT", "Expectant"),
        ],
        description="Relationship to the casualty.",
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
    triage_criteria = TextAreaField(
        "Triage Criteria", description="Detailed criteria for the triage category."
    )
    triage_description = TextAreaField(
        "Triage Description",
        description="A one-line description of the tagLabel category.",
    )

    submit = SubmitField("Save Casualty")


class VitalsForm(FlaskForm):
    heart_rate = IntegerField(
        "Heart Rate",
        validators=[NumberRange(min=0)],
        description="Heart rate in beats per minute.",
    )
    blood_pressure = StringField(
        "Blood Pressure",
        description="Blood pressure in mmHg.",
    )
    oxygen_saturation = StringField(
        "Oxygen Saturation",
        description="Oxygen saturation in percent.",
    )
    respiratory_rate = StringField(
        "Respiratory Rate",
        description="Respiratory rate in breaths per minute.",
    )
    pain = StringField(
        "Pain",
        description="Pain level on a scale of 0-10.",
    )

    breathing = SelectField(
        "Breathing",
        choices=[
            ("", ""),
            ("NORMAL", "NORMAL"),
            ("FAST", "FAST"),
            ("RESTRICTED", "RESTRICTED"),
            ("NONE", "NONE"),
        ],
        description="A descriptor for the casualty's breathing.",
    )

    concious = SelectField(
        "Concious",
        choices=[
            ("", ""),
            ("true", True),
            ("false", False),
        ],
        description="Conciousness status.",
    )
    mental_status = SelectField(
        "Mental Status",
        choices=[
            # ("A", "A"),
            # ("V", "V"),
            # ("P", "P"),
            # ("U", "U"),
            ("", ""),
            ("AGONY", "AGONY"),
            ("CALM", "CALM"),
            ("CONFUSED", "CONFUSED"),
            ("UPSET", "UPSET"),
            ("UNRESPONSIVE", "UNRESPONSIVE"),
        ],
        description="Mental status. Should be A V P U",
    )

    submit = SubmitField("Save Vitals")


class InjuryForm(FlaskForm):
    injury_location = SelectField(
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
            ("RIGHT_WRIST", "right wrist"),
            ("LEFT_WRIST", "left wrist"),
            ("LEFT_FACE", "left face"),
            ("RIGHT_FACE", "right face"),
            ("LEFT_KNECK", "left neck"),
            ("RIGHT_NECK", "right neck"),
        ],
        description="Location of the injury.",
    )
    injury_type = SelectField(
        "Name",
        choices=[
            ("", ""),
            ("FOREHEAD_SCRAPE", "Forehead Scrape"),
            ("EAR_BLEED", "Ear Bleed"),
            ("ASTHMATIC", "Asthmatic"),
            ("LACERATION", "Laceration"),
            ("PUNCTURE", "Puncture"),
            ("SHRAPNEL", "Shrapnel"),
            ("CHEST_COLLAPSE", "Chest Collapse"),
            ("AMPUTATION", "Amputation"),
            ("BURN", "Burn"),
        ],
    )
    injury_severity = StringField(
        "severity",
        description="Apparent severity of the injury from 0 (low) to 1.0 (high).",
    )
    submit = SubmitField("Save Injury")


class SupplyForm(FlaskForm):
    supply_type = SelectField(
        "Type",
        choices=[
            ("", ""),
            ("TOURNIQUET", "Tourniquet"),
            ("PRESSURE_BANDAGE", "Pressure bandage"),
            ("HEMOSTATIC_GAUZE", "Hemostatic gauze"),
            ("DECOMPRESSION_NEEDLE", "Decompression Needle"),
            ("NASOPHARYNGEAL_AIRWAY", "Nasopharyngeal airway"),
        ],
        description="A single type of medical supply available to the medic",
    )
    supply_quantity = IntegerField(
        "Quantity",
        validators=[NumberRange(min=0)],
        description="Quantity of the supply.",
        default=0,
    )
    submit = SubmitField("Save Supply")


class ThreatForm(FlaskForm):
    threat_type = StringField(
        "Type", description="Type of threat. E.g., IED, enemy fire, etc."
    )
    threat_severity = FloatField(
        "Severity",
        validators=[NumberRange(min=0, max=1)],
        description="Severity of the threat from 0 (no threat) to 1.0 (max threat).",
    )
    submit = SubmitField("Save Threat")


class EnvironmentForm(FlaskForm):
    aid_delay = StringField(
        "Aid Delay",
        description="Time until tactical evacuation or exfiltration in minutes.",
    )
    fauna = StringField("Fauna", description="Fauna in the area.")
    flora = StringField("Flora")
    humidity = StringField("Humidity", description="Relative humidity in percent.")
    lighting = StringField(
        "Lighting",
        description="A numeric indicator (0-1) of current ligting conditions (natural or man-made); lower is darker.",
    )
    location = StringField(
        "Location", description="Description of where the scenario takes place."
    )
    noise_ambient = StringField(
        "Ambient Noise",
        description="A numeric indicator (0-1) of ambient noise at the scenario location; higher is louder.",
    )
    noise_peak = StringField(
        "Peak Noise",
        description="A numeric indicator (0-1) of peak noise; higher is louder.",
    )
    soundscape = StringField(
        "Soundscape", description="A natural language description of the soundscape."
    )
    temperature = StringField(
        "Temperature", description="Temperature in degrees Farenheit."
    )
    terrain = StringField(
        "Terrain", description="A natural language description of the terrain."
    )
    visibility = StringField(
        "Visibility",
        description="A numeric indicator (0-1) of visibility; higher is clearer, lower is darker. Affected by time of day, terrain, etc.",
    )
    weather = StringField(
        "Weather", description="A natural language description of the weather."
    )
    unstructured = TextAreaField(
        "Unstructured", description="Unstructured field for additional information."
    )

    submit = SubmitField("Save Environment")
