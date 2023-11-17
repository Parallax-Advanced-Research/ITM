from app import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text, Boolean, Float


class Scenario(db.Model):
    __tablename__ = "scenario"
    id = db.Column(Integer, primary_key=True)
    time_stamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    description = db.Column(Text, nullable=True)  # TA3 State Description
    mission_description = db.Column(Text, nullable=True)
    mission_type = db.Column(String(50), nullable=True)
    casualties = db.relationship(
        "Casualty", secondary="casualty_scenario", backref="scenarios", lazy="dynamic"
    )
    probes = db.relationship("Probe", backref="scenario", lazy=True)
    threat_state_description = db.Column(String(50), nullable=True)
    threats = db.relationship("Threat", backref="scenario", lazy=True)
    supplies = db.relationship("Supply", backref="scenario", lazy=True)
    elapsed_time = db.Column(String, nullable=True)
    environment = db.relationship("Environment", backref="scenario", lazy=True)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<Scenario {}>".format(self.description)


class Environment(db.Model):
    __tablename__ = "environment"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    aid_delay = db.Column(String, nullable=True)
    fauna = db.Column(String, nullable=True)
    flora = db.Column(String, nullable=True)
    humidity = db.Column(String, nullable=True)
    lighting = db.Column(String, nullable=True)
    location = db.Column(String, nullable=True)
    noise_ambient = db.Column(String, nullable=True)
    noise_peak = db.Column(String, nullable=True)
    soundscape = db.Column(String, nullable=True)
    temperature = db.Column(String, nullable=True)
    terrain = db.Column(String, nullable=True)
    unstructured = db.Column(String, nullable=True)
    visibility = db.Column(String, nullable=True)
    weather = db.Column(String, nullable=True)
    scenario_id = db.Column(Integer, ForeignKey("scenario.id"), nullable=True)

    def as_dict(self):
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue
            yield key, value


class Threat(db.Model):
    __tablename__ = "threat"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    threat_type = db.Column(String(50), nullable=True)
    threat_severity = db.Column(String(50), nullable=True)
    scenario_id = db.Column(Integer, ForeignKey("scenario.id"), nullable=True)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<Threat {} ({})>".format(self.threat_type, self.threat_severity)


class Casualty(db.Model):
    __tablename__ = "casualty"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    name = db.Column(String(50), nullable=False, default="casualty " + id)
    description = db.Column(String(50), nullable=True)  # ta3= unstructured
    visited = db.Column(Boolean, nullable=True, default=False)  # ta3 column

    # demographics
    age = db.Column(Integer, nullable=True)  # ta3=demogrphics.age
    sex = db.Column(String(50), nullable=True)  # ta3=demogrphics.sex
    rank = db.Column(String(50), nullable=True)  # ta3=demogrphics.rank
    relationship_type = db.Column(String(50), nullable=True)  # ta3=relationship
    triage_criteria = db.Column(String(50), nullable=True)
    triage_description = db.Column(String(50), nullable=True)
    tag_label = db.Column(String(50), nullable=True)  # ta3=tag

    injuries = db.relationship(
        "Injury", backref="casualty", lazy=True, cascade="all, delete"
    )
    vitals = db.relationship(
        "Vitals",
        secondary="casualty_vitals",
        backref="casualty",
        lazy="dynamic",
        cascade="all, delete",
    )
    actions = db.relationship("Action", backref="casualty", lazy=True)

    def get_feature_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "visited": self.visited,
            "age": self.age,
            "sex": self.sex,
            "rank": self.rank,
            "relationship_type": self.relationship_type,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<Casualty {}>".format(self.name)


class Injury(db.Model):
    __tablename__ = "injury"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    injury_type = db.Column(String(50), nullable=True)
    injury_severity = db.Column(String(50), nullable=True)
    injury_location = db.Column(String(50), nullable=True)
    # injury_treated = db.Column(Boolean, nullable=True, default=False)
    casualty_id = db.Column(Integer, ForeignKey("casualty.id"), nullable=True)

    def get_feature_dict(self):
        return {
            "injury_type": self.injury_type,
            "injury_severity": self.injury_severity,
            "injury_location": self.injury_location,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<Injury {}>".format(self.injury_type)


class Vitals(db.Model):
    __tablename__ = "vitals"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    heart_rate = db.Column(Integer, nullable=True)
    blood_pressure = db.Column(Integer, nullable=True)
    oxygen_saturation = db.Column(Integer, nullable=True)
    respiratory_rate = db.Column(Integer, nullable=True)
    pain = db.Column(Integer, nullable=True)
    breathing = db.Column(String(50), nullable=True)
    concious = db.Column(String(50), nullable=True)
    mental_status = db.Column(String(50), nullable=True)

    def get_feature_dict(self):
        return {
            "heart_rate": self.heart_rate,
            "blood_pressure": self.blood_pressure,
            "oxygen_saturation": self.oxygen_saturation,
            "respiratory_rate": self.respiratory_rate,
            "pain": self.pain,
            "breathing": self.breathing,
            "concious": self.concious,
            "mental_status": self.mental_status,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<Vitals {}>".format(self.heart_rate)


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


class Supply(db.Model):
    __tablename__ = "supply"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    supply_type = db.Column(String(50), nullable=True)
    supply_quantity = db.Column(Integer, nullable=True)
    timestamp = db.Column(DateTime, nullable=False, default=datetime.utcnow)
    scenario_id = db.Column(Integer, ForeignKey("scenario.id"), nullable=True)

    def get_feature_dict(self):
        return {
            "supply_type": self.supply_type,
            "supply_quantity": self.supply_quantity,
        }

    def get_single_feature_dict(self):
        return {
            self.supply_type: self.supply_quantity,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<Supply {}>".format(self.supply_type)
