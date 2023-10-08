from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime
from typing import Optional
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import BaseModel, Field, parse_obj_as
from pydantic.json import pydantic_encoder


class Base(DeclarativeBase):
    __abstract__ = True

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, self.__dict__)

    def __str__(self):
        return self.__repr__()


class CaseBase(Base):
    __abstract__ = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._case_id = None

    @property
    def case_id(self):
        return self._case_id

    @case_id.setter
    def case_id(self, value):
        self._case_id = value


class Case(CaseBase):
    __tablename__ = "case"

    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    case_created_date = Column(DateTime, nullable=False)
    case_updated_date = Column(DateTime, nullable=False)
    case_created_by = Column(String(50), nullable=False)
    case_updated_by = Column(String(50), nullable=False)


class Action(Base):
    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)


class CaseHistory(Base):
    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    case_history = Column(String(50), nullable=False)
    case_history_value = Column(String(50), nullable=False)
    case_history_unit = Column(String(50), nullable=False)
    case_history_date = Column(DateTime, nullable=False)
    case_history_time = Column(DateTime, nullable=False)
    case_history_created_by = Column(String(50), nullable=False)
    case_history_updated_by = Column(String(50), nullable=False)
    case_history_updated_date = Column(DateTime, nullable=False)


class Casualty(Base):
    __tablename__ = "casualty"

    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)


class Decision(Base):
    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    decision = Column(String(50), nullable=False)
    decision_value = Column(String(50), nullable=False)


class Demographics(Base):
    __tablename__ = "demographics"

    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    demographics = Column(String(50), nullable=False)
    demographics_value = Column(String(50), nullable=False)
    demographics_unit = Column(String(50), nullable=False)
    demographics_date = Column(DateTime, nullable=False)
    demographics_time = Column(DateTime, nullable=False)
    demographics_created_by = Column(String(50), nullable=False)
    demographics_updated_by = Column(String(50), nullable=False)
    demographics_updated_date = Column(DateTime, nullable=False)


class Environment(Base):
    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    environment = Column(String(50), nullable=False)
    environment_value = Column(String(50), nullable=False)
    environment_unit = Column(String(50), nullable=False)
    environment_date = Column(DateTime, nullable=False)
    environment_time = Column(DateTime, nullable=False)
    environment_created_by = Column(String(50), nullable=False)
    environment_updated_by = Column(String(50), nullable=False)
    environment_updated_date = Column(DateTime, nullable=False)


class KDMA(Base):
    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    kdma = Column(String(50), nullable=False)
    kdma_value = Column(String(50), nullable=False)
    kdma_unit = Column(String(50), nullable=False)
    kdma_date = Column(DateTime, nullable=False)
    kdma_time = Column(DateTime, nullable=False)
    kdma_created_by = Column(String(50), nullable=False)
    kdma_updated_by = Column(String(50), nullable=False)
    kdma_updated_date = Column(DateTime, nullable=False)


class Supply(CaseBase):
    __tablename__ = "supply"

    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    supply = Column(String(50), nullable=False)
    supply_value = Column(String(50), nullable=False)
    supply_unit = Column(String(50), nullable=False)
    supply_date = Column(DateTime, nullable=False)
    supply_time = Column(DateTime, nullable=False)
    supply_created_by = Column(String(50), nullable=False)
    supply_updated_by = Column(String(50), nullable=False)
    supply_updated_date = Column(DateTime, nullable=False)


class Scenario(Base):
    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    scenario = Column(String(50), nullable=False)
    scenario_value = Column(String(50), nullable=False)
    scenario_unit = Column(String(50), nullable=False)
    scenario_date = Column(DateTime, nullable=False)
    scenario_time = Column(DateTime, nullable=False)
    scenario_created_by = Column(String(50), nullable=False)
    scenario_updated_by = Column(String(50), nullable=False)
    scenario_updated_date = Column(DateTime, nullable=False)


class Treatment(Base):
    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    treatment = Column(String(50), nullable=False)
    treatment_value = Column(String(50), nullable=False)
    treatment_unit = Column(String(50), nullable=False)
    treatment_date = Column(DateTime, nullable=False)
    treatment_time = Column(DateTime, nullable=False)
    treatment_created_by = Column(String(50), nullable=False)
    treatment_updated_by = Column(String(50), nullable=False)
    treatment_updated_date = Column(DateTime, nullable=False)


class TriageCategory(Base):
    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    triage_category = Column(String(50), nullable=False)
    triage_category_value = Column(String(50), nullable=False)
    triage_category_unit = Column(String(50), nullable=False)
    triage_category_date = Column(DateTime, nullable=False)
    triage_category_time = Column(DateTime, nullable=False)
    triage_category_created_by = Column(String(50), nullable=False)
    triage_category_updated_by = Column(String(50), nullable=False)
    triage_category_updated_date = Column(DateTime, nullable=False)


class Vitals(Base):
    __tablename__ = "vitals"

    id = Column(Integer, primary_key=True)
    case_id = Column(String(50), nullable=False)
    vitals = Column(String(50), nullable=False)
    vitals_value = Column(String(50), nullable=False)
    vitals_unit = Column(String(50), nullable=False)
    vitals_date = Column(DateTime, nullable=False)
    vitals_time = Column(DateTime, nullable=False)
    vitals_created_by = Column(String(50), nullable=False)
    vitals_updated_by = Column(String(50), nullable=False)
    vitals_updated_date = Column(DateTime, nullable=False)
