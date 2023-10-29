from app import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
import enum


class ExtendedEnum(enum.Enum):
    @classmethod
    def get_members(cls):
        return [member.value for name, member in cls.__members__.items()]

    @classmethod
    def get_member(cls, value):
        return cls.__members__.get(value, None)

    @classmethod
    def get_member_name(cls, value):
        member = cls.get_member(value)
        return member.name if member else None

    @classmethod
    def get_member_value(cls, name):
        member = cls.__members__.get(name, None)
        return member.value if member else None


class MissionTypes(ExtendedEnum):
    LISTENING_OBSERVATION = "Listening/Observation"
    DIRECT_ACTION = "Direct Action"
    HOSTAGE_RESCUE = "Hostage rescue"
    ASSET_TRANSPORT = "Asset transport"
    SENSOR_EMPLACEMENT = "Sensor emplacement"
    INTELLIGENCE_GATHERING = "Intelligence gathering"
    CIVIL_AFFAIRS = "Civil affairs"
    TRAINING = "Training"
    SABOTAGE = "Sabotage"
    SECURITY_PATROL = "Security patrol"
    FIRE_SUPPORT = "Fire support"
    NUCLEAR_DETERRENCE = "Nuclear deterrence"
    EXTRACTION = "Extraction"
    UNKNOWN = "Unknown"


class SupplyTypes(ExtendedEnum):
    TOURNIQUET = "Tourniquet"
    PRESSURE_BANDAGE = "Pressure bandage"
    HEMOSTATIC_GAUZE = "Hemostatic gauze"
    DECOMPRESSION_NEEDLE = "Decompression Needle"  # in ta1 data Decompression Needle
    NASPHARYNGEAL_AIRWAY = "Nasopharyngeal airway"


class RelationshipTypes(ExtendedEnum):
    NONE = "None"
    ALLY = "Ally"
    FRIEND = "Friend"
    HOSTILE = "Hostile"
    EXPECTANT = "Expectant"


class RankTypes(ExtendedEnum):
    MARINE = "Marine"
    FMF_CORPSMAN = "FMF Corpsman"
    SAILOR = "Sailor"
    CIVILIAN = "Civilian"
    SEAL = "SEAL"
    INTEL_OFFICER = "Intel Officer"


class CaseBase(db.Model):
    __tablename__ = "casebase"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    description = db.Column(db.String(256))
    created_by = db.Column(db.String(64), default="admin")
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    cases = db.relationship("Case", backref="casebase", lazy="dynamic")


class Case(db.Model):
    __tablename__ = "case"
    id = db.Column(Integer, primary_key=True)
    external_id = db.Column(String(50), nullable=True)
    name = db.Column(String(50), nullable=False, default="case " + id)
    time_stamp = db.Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    casebase_id = db.Column(Integer, db.ForeignKey("casebase.id"), nullable=False)
    scenarios = db.relationship(
        "Scenario",
        secondary="case_scenario",
        backref="cases",
        lazy="dynamic",
        cascade="all, delete",
    )

    def save(self):
        db.session.add(self)
        db.session.commit()


case_scenario = db.Table(
    "case_scenario",
    db.Model.metadata,
    db.Column("case_id", db.Integer, db.ForeignKey("case.id")),
    db.Column("scenario_id", db.Integer, db.ForeignKey("scenario.id")),
)
