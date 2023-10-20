from app import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
from app.case.models import Case, case_scenario


class Scenario(db.Model):
    __tablename__ = "scenario"
    id = db.Column(Integer, primary_key=True)
    time_stamp = db.Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    description = db.Column(Text, nullable=True)
    mission_description = db.Column(Text, nullable=True)
    mission_type = db.Column(String(50), nullable=True)
    casualties = db.relationship(
        "Casualty", secondary="casualty_scenario", backref="scenarios", lazy="dynamic"
    )
    probes = db.relationship("Probe", backref="scenario", lazy=True)
    threat_state_description = db.Column(String(50), nullable=True)
    threats = db.relationship("Threat", backref="scenario", lazy=True)
    supplies = db.relationship("Supply", backref="scenario", lazy=True)

    def save(self):
        db.session.add(self)
        db.session.commit()


class Threat(db.Model):
    __tablename__ = "threat"
    id = db.Column(Integer, primary_key=True)
    threat_type = db.Column(String(50), nullable=True)
    threat_severity = db.Column(String(50), nullable=True)
    scenario_id = db.Column(Integer, ForeignKey("scenario.id"), nullable=True)


class Casualty(db.Model):
    __tablename__ = "casualty"
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(50), nullable=False, default="casualty " + id)
    description = db.Column(String(50), nullable=True)
    # demographics
    age = db.Column(Integer, nullable=True)
    sex = db.Column(String(50), nullable=True)
    rank = db.Column(String(50), nullable=True)
    relationship_type = db.Column(String(50), nullable=True)
    vitals = db.relationship(
        "Vitals",
        secondary="casualty_vitals",
        backref="casualty",
        lazy="dynamic",
        cascade="all, delete",
    )


class Vitals(db.Model):
    __tablename__ = "vitals"
    id = db.Column(Integer, primary_key=True)
    heart_rate = db.Column(Integer, nullable=True)
    blood_pressure = db.Column(Integer, nullable=True)
    oxygen_saturation = db.Column(Integer, nullable=True)
    respiratory_rate = db.Column(Integer, nullable=True)
    pain = db.Column(Integer, nullable=True)
    mental_status = db.Column(String(50), nullable=True)
    timestamp = db.Column(DateTime, nullable=False, default=datetime.utcnow)
    concious = db.Column(String(50), nullable=True)


class Supply(db.Model):
    __tablename__ = "supply"
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(50), nullable=False, default="supply " + id)
    description = db.Column(String(50), nullable=True)
    quantity = db.Column(Integer, nullable=True)
    unit = db.Column(String(50), nullable=True)
    timestamp = db.Column(DateTime, nullable=False, default=datetime.utcnow)
    scenario_id = db.Column(Integer, ForeignKey("scenario.id"), nullable=True)


casualty_scenario = db.Table(
    "casualty_scenario",
    db.Model.metadata,
    db.Column("casualty_id", db.Integer, db.ForeignKey("casualty.id")),
    db.Column("scenario_id", db.Integer, db.ForeignKey("scenario.id")),
)

casualty_vitals = db.Table(
    "casualty_vitals",
    db.Model.metadata,
    db.Column("casualty_id", db.Integer, db.ForeignKey("casualty.id")),
    db.Column("vitals_id", db.Integer, db.ForeignKey("vitals.id")),
)
