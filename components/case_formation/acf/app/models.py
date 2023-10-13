import enum
from components.case_formation.acf.app import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime


class CaseBase(db.Model):
    __tablename__ = "case_base"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, default="case base " + id, unique=True)
    description = Column(String(255), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String(50), nullable=True)
    cases = db.relationship("Case", backref="case_base", lazy="dynamic")


class Case(db.Model):
    __tablename__ = "case"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, default="case " + id)
    time_stamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String(50), nullable=True)
    case_base_id = Column(Integer, db.ForeignKey("case_base.id"), nullable=False)
    scenarios = db.relationship("Scenario", backref="case", lazy="dynamic")


class Scenario(db.Model):
    __tablename__ = "scenario"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, default="scenario " + id)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String(50), nullable=True)
    case_id = Column(Integer, db.ForeignKey("case.id"), nullable=False)
    scenario_items = db.relationship("ScenarioItem", backref="scenario", lazy="dynamic")


class ScenarioItem(db.Model):
    __tablename__ = "scenario_item"
    id = Column(Integer, primary_key=True)
    item_name = Column(String(50), nullable=False)
    item_type = Column(String(50), nullable=False)
    item_value = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String(50), nullable=True)
    scenario_id = Column(Integer, db.ForeignKey("scenario.id"), nullable=False)
