import sys
from app import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text, Float, Boolean
import builtins, inspect
import typing

from app.probe.models import Probe
from app.scenario.models import Scenario

# give access to top level modules
# sys.path.append("../../../../")  # TODO: fix this hack
sys.path.append("D:\Code\itm-local")
import domain.internal as TAD
import domain.ta3 as TA3
from components import DecisionAnalyzer
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer
from components.decision_analyzer.event_based_diagnosis import (
    EventBasedDiagnosisAnalyzer,
)
import random

# import tinymed enums
import components.decision_analyzer.monte_carlo.medsim.util.medsim_enums as tinymed_enums

T = typing.TypeVar("T")


def normalize_enum(value, enum):
    return enum(value).value


# this is here instead of in the probe object so we can run the casebase outside of the TAD repo
# once we have unified them, we can move it back
def convert_to_tad_probe(TADScenario, Probe) -> TAD.TADProbe:
    probe_id = Probe.probe_id
    probe_state = TADScenario.state
    probe_prompt = Probe.prompt
    probe_decisions = []
    tad_probe = TAD.TADProbe(probe_id, probe_state, probe_prompt, probe_decisions)
    return tad_probe


def convert_to_ta3_injury(Injury) -> TA3.Injury:
    # TA3               # TADTA3            # Model
    # location
    # # InjuryLocation  # location          # injury_location
    # name              # name              # injury_type
    # severity          # severity          # injury_severity
    # treated           # treated           # -----

    injury_location = Injury.injury_location
    injury_name = Injury.injury_type
    injury_severity = float(Injury.injury_severity)
    injury_treated = False  # TODO: change to a real value

    injury_name = injury_name.split("_")
    if len(injury_name) > 1:
        injury_name = injury_name.title() + " " + injury_name[1].lower()
    else:
        injury_name = injury_name[0].title()

    ta3_injury = TA3.Injury(
        location=injury_location,
        name=injury_name.title(),
        severity=injury_severity,
        treated=injury_treated,
    )

    return ta3_injury


def convert_to_ta3_injuries(Injuries) -> list[TA3.Injury]:
    ta3_injuries = []
    for Injury in Injuries:
        ta3_injury = convert_to_ta3_injury(Injury)
        ta3_injuries.append(ta3_injury)
    return ta3_injuries


def convert_to_ta3_demographics(Casualty) -> TA3.Demographics:
    # TA3               # TADTA3            # Model
    # age               # age               # age
    # [rank]            # rank              # rank
    # [sex]             # sex               # sex
    # relationship_type

    casualty_age = Casualty.age
    casualty_sex = Casualty.sex
    casualty_rank = Casualty.rank

    ta3_demographics = TA3.Demographics(
        age=casualty_age, sex=casualty_sex, rank=casualty_rank
    )
    return ta3_demographics


def convert_to_ta3_vitals(Vitals) -> TA3.Vitals:
    # TA3               # TADTA3            # Model
    # concious          # conscious         # conscious
    # [mental_status]   # mental_status     # mental_status
    # breathing         # breathing         # breathing
    # hrpmin            # hrpmin            # heart_rate

    vitals_conscious = Vitals[0].concious
    vitals_mental_status = Vitals[0].mental_status
    vitals_breathing = Vitals[0].breathing
    vitals_hrpmin = Vitals[0].heart_rate

    ta3_vitals = TA3.Vitals(
        conscious=vitals_conscious,
        mental_status=vitals_mental_status,
        breathing=vitals_breathing,
        hrpmin=vitals_hrpmin,
    )
    return ta3_vitals


def convert_to_ta3_casualty(Casualty) -> TA3.Casualty:
    # TA3               # TADTA3            # Model
    # id                # id                # id
    # name              # name              # name
    # injuries          # injuries          # [injuries]
    # demographics      # Demographics      # [demographics]
    # vitals            # Vitals            # [vitals]
    # tag               # tag               # tag_label
    # relationship      # relationship      # relationship_type
    # unstructured      # unstructured      # description
    # visited           # assessed          # visted
    # ----------        # [treatments]        # -----------

    casualty_id = Casualty.id
    casualty_name = Casualty.name
    casualty_injuries = convert_to_ta3_injuries(Casualty.injuries)
    casualty_demographics = convert_to_ta3_demographics(Casualty)
    casualty_vitals = convert_to_ta3_vitals(Casualty.vitals)
    casualty_tag = Casualty.tag_label
    casualty_relationship = Casualty.relationship_type
    casualty_unstructured = Casualty.description
    casualty_assessed = Casualty.visited
    casualty_treatments = []

    ta3_casualty = TA3.Casualty(
        id=casualty_id,
        name=casualty_name,
        injuries=casualty_injuries,
        demographics=casualty_demographics,
        vitals=casualty_vitals,
        tag=casualty_tag,
        relationship=casualty_relationship,
        unstructured=casualty_unstructured,
        assessed=casualty_assessed,
        treatments=casualty_treatments,
    )

    return ta3_casualty


def convert_to_ta3_casualties(Casualties) -> list[TA3.Casualty]:
    ta3_casualties = []
    for Casualty in Casualties:
        ta3_casualty = convert_to_ta3_casualty(Casualty)
        ta3_casualties.append(ta3_casualty)
    return ta3_casualties


def convert_to_ta3_supply(Supply) -> TA3.Supply:
    # TA3               # TADTA3            # Model
    # type              # type              # supply_type
    # quantity          # quantity          # supply_quantity

    supply_type = Supply.supply_type
    supply_quantity = Supply.supply_quantity

    ta3_supply = TA3.Supply(type=supply_type, quantity=supply_quantity)
    return ta3_supply


def convert_to_ta3_supplies(Supplies) -> list[TA3.Supply]:
    ta3_supplies = []
    for Supply in Supplies:
        ta3_supply = convert_to_ta3_supply(Supply)
        ta3_supplies.append(ta3_supply)
    return ta3_supplies


# convert string to float or int if possible otherwise return 0
def try_get(obj, prop):
    obj_prop = getattr(obj, prop, 0)
    return obj_prop


def convert_to_ta3_state(Scenario) -> TA3.TA3State:
    unstructured = Scenario.description
    casualties = convert_to_ta3_casualties(Scenario.casualties)
    supplies = convert_to_ta3_supplies(Scenario.supplies)
    time = 0
    ta3_state = TA3.TA3State(
        unstructured=unstructured, casualties=casualties, supplies=supplies, time_=time
    )
    return ta3_state
    # now we need to add actions performed and treatments in the probe


def convert_to_tad_scenario(Scenario) -> TAD.Scenario:
    # TAD Scenario is
    # id_: str

    # state: TAD.State
    tad_state = convert_to_ta3_state(Scenario)

    tad_scenario = TAD.Scenario(Scenario.id, tad_state)
    return tad_scenario


class ProbeToAnalyze(Probe):
    def __init__(self, probe: Probe, decision_analyzer: DecisionAnalyzer):
        self.probe = probe
        self.decision_analyzer = decision_analyzer

    def as_tad_probe(self, tad_scenario) -> TAD.TADProbe:
        return convert_to_tad_probe(tad_scenario, self.probe)

    def as_tad_scenario(self) -> TAD.Scenario:
        return convert_to_tad_scenario(self.probe.scenario)

    # MC Analyzers should show output can't be given because of supply list

    def analyze(self):
        tad_scenario = self.as_tad_scenario()
        tad_probe = self.as_tad_probe(tad_scenario)
        for probe_response in self.probe.responses:
            # send the whole probe to decision analytics as separate actions
            for action in probe_response.actions:
                casualty = action.casualty
                param_dict = {}
                param_dict["casualty"] = casualty.name
                for param in action.parameters:
                    param_dict[param.parameter_type] = param.parameter_value
                tad_action = TAD.Action(action.action_type, param_dict)
                tad_decision = TAD.Decision(
                    id_="action1",
                    value=tad_action,
                    justifications=[],
                    metrics={},
                    kdmas=None,
                )

                tad_probe.decisions = tad_decision
                # give them one of each of the supplies if it is a monte carlo analyzer
                # this is because monte carlo only handles a subset of supplies (in tinymed_enums.Supplies)
                if isinstance(self.decision_analyzer, MonteCarloAnalyzer):
                    supplies_list = []
                    for supply in tinymed_enums.Supplies:
                        supply = TA3.Supply(supply.value, 1)
                        supplies_list.append(supply)
                    tad_scenario.state.supplies = supplies_list
                result = self.decision_analyzer.analyze(tad_scenario, tad_probe)
                print(result)
        # figure out how to return a bunch of decisions, maybe a db table?
        # if the decision_analyzer is a MonteCarloDecisionAnalyzer, we need to check if the supplies are empty
        is_mc = isinstance(self.decision_analyzer, MonteCarloAnalyzer)
        if isinstance(self.decision_analyzer, MonteCarloAnalyzer):
            if not tad_scenario.state.supplies:
                return "No supplies available to run Monte Carlo Analysis"

        return self.decision_analyzer.analyze(tad_scenario, tad_probe)

    @classmethod
    def __str__(self):
        return self.probe.prompt


"""
class ProbeConverter(db.TypeDecorator):
    impl = db.String

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.to_json()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Probe.from_json(value)


class ProbeAnalysis:
    __tablename__ = "probe_analysis"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    probe_id = db.Column(String, nullable=True)
    decision_metrics = db.relationship("DecisionMetric", backref="probe_analysis")


class DecisionMetric(TAD.DecisionMetric[T]):
    __tablename__ = "decision_metric"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    name = db.Column(String(50), nullable=True)
    description = db.Column(String(50), nullable=True)
    value = db.Column(String(50), nullable=True)
    probe_analysis_id = db.Column(
        Integer, ForeignKey("probe_analysis.id"), nullable=True
    )

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
"""
