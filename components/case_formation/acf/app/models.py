import enum
from components.case_formation.acf.app import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime


class CaseBase(db.Model):
    __tablename__ = "case_base"
    id = Column(Integer, primary_key=True)
    case_base_id = Column(String(50), nullable=False)
    case_base_name = Column(String(50), nullable=False)
    case_base_created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    case_base_updated_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    case_base_created_by = Column(String(50), nullable=True)
    case_base_updated_by = Column(String(50), nullable=True)
    cases = db.relationship("Case", backref="case_base", lazy="dynamic")


class Case(db.Model):
    __tablename__ = "case"

    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), default="case " + id, nullable=False)
    case_created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    case_updated_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    case_created_by = Column(String(50), nullable=True)
    case_updated_by = Column(String(50), nullable=True)
    case_base_id = Column(Integer, db.ForeignKey("case_base.id"), nullable=False)
