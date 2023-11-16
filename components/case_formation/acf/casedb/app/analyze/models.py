import sys
from app import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text, Float, Boolean
import builtins, inspect
import typing
from util.dict_tools import Dict_No_Overwrite

sys.path.append("../../../../")
import domain.internal as TAD
import domain.ta3 as TA3
import components.decision_analyzer as DA


T = typing.TypeVar("T")


class ProbeDecisionAnalysis:
    __tablename__ = "probe_analysis"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    probe_id = db.Column(String, nullable=True)


class DecisionMetric(TAD.DecisionMetric[T]):
    __tablename__ = "decision_metric"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    name = db.Column(String(50), nullable=True)
    description = db.Column(String(50), nullable=True)
    value = db.Column(String(50), nullable=True)

    def as_tad(self) -> TAD.DecisionMetric[T]:
        return TAD.DecisionMetric(self.name, self.description, self.value)

    def __init__(self, name: str, description: str, value: T):
        self.name: str = name
        self.description: str = description
        self.value: T = value


class Decision(TAD.Decision):
    __tablename__ = "decision"

    def __init__(
        self,
        id_: str,
        value: T,
        justifications: list[TAD.Justification] = (),
        metrics: typing.Mapping[TAD.DecisionName, TAD.DecisionMetric] = None,
        kdmas: TAD.KDMAs = None,
    ):
        self.id_: str = id_
        self.value: T = value
        self.justifications: list[TAD.Justification] = justifications
        self.metrics: TAD.DecisionMetrics = Dict_No_Overwrite()
        if metrics:
            self.metrics.update(metrics)
        self.kdmas: TAD.KDMAs | None = kdmas


class Action(TAD.Action):
    __tablename__ = "action"

    def __init__(self, name_: str, params: dict[str, typing.Any]):
        self.name: str = name_
        self.params: dict[str, typing.Any] = params

    def __str__(self):
        return f"{self.name}({','.join(self.params.values())})"

    def to_json(self):
        d = dict()

        def get_params(params):
            dd = {}
            for param in self.params:
                dd[param] = params[param]
            return dd

        d["name"] = self.name
        d["params"] = get_params(self.params)
        return d

    # This makes it so that actions can be shown in the logger nicer
    # def __repr__(self):
    #     return self.__str__()
