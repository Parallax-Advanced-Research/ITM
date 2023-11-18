from app import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text, Float, Boolean
import sys


current_path = sys.path[0]
sys.path.append(current_path + "/../../../../")


import domain.internal as TAD
import domain.ta3 as TA3
from components import DecisionAnalyzer
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer
from components.decision_analyzer.event_based_diagnosis import (
    EventBasedDiagnosisAnalyzer,
)

# import tinymed enums
import components.decision_analyzer.monte_carlo.medsim.util.medsim_enums as tinymed_enums


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
        id=casualty_name,  # TODO: use instead of the db id for mc analysis
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


class Probe(db.Model):
    __tablename__ = "probe"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    probe_id = db.Column(String, nullable=True)
    type = db.Column(String(50), nullable=True)
    prompt = db.Column(String(50), nullable=True)
    state = db.Column(String(50), nullable=True)
    options = db.relationship("ProbeOption", backref="probe", lazy=True)
    responses = db.relationship("ProbeResponse", backref="probe", lazy=True)
    scenario_id = db.Column(Integer, ForeignKey("scenario.id"), nullable=True)

    def get_feature_dict(self):
        return {
            "type": self.type,
            "prompt": self.prompt,
        }

    def as_tad_probe(self, tad_scenario) -> TAD.TADProbe:
        return convert_to_tad_probe(tad_scenario, self)

    def as_tad_scenario(self) -> TAD.Scenario:
        return convert_to_tad_scenario(self.scenario)

    def analyze(self):
        decision_analyzer = MonteCarloAnalyzer(max_rollouts=1000, max_depth=2)
        tad_scenario = self.as_tad_scenario()
        tad_probe = self.as_tad_probe(tad_scenario)

        is_mc = isinstance(decision_analyzer, MonteCarloAnalyzer)
        if is_mc:
            supplies_list = []
            for supply in tinymed_enums.Supplies:
                supply = TA3.Supply(supply.value, 10)
                supplies_list.append(supply)
            tad_scenario.state.supplies = supplies_list

        decision_actions = []
        for probe_response in self.responses:
            # send the whole probe to decision analytics as separate actions
            KDMAs = []
            for kdma in probe_response.kdmas:
                # new internal kdma object
                tad_kdma = TAD.KDMA(id_=kdma.kdma_name, value=kdma.kdma_value)
                KDMAs.append(tad_kdma)

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
                    kdmas=TAD.KDMAs(KDMAs),
                )
                decision_actions.append(tad_decision)
                tad_probe.state.actions_performed = [tad_action]

        # remove duplicates when value.name and parameters are the same
        for decision_action in decision_actions:
            for other_decision_action in decision_actions:
                if (
                    decision_action.value.name == other_decision_action.value.name
                    and decision_action.value.params
                    == other_decision_action.value.params
                    and decision_action != other_decision_action
                ):
                    decision_actions.remove(other_decision_action)

        # renumber the decision_actions consecutively
        for i, decision_action in enumerate(decision_actions):
            decision_action.id_ = "action" + str(i + 1)

        tad_probe.decisions = decision_actions

        metrics = decision_analyzer.analyze(tad_scenario, tad_probe)

        return metrics

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<Probe {}>".format(self.probe_id)


class ProbeOption(db.Model):
    __tablename__ = "probe_option"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    choice_id = db.Column(String, nullable=True)
    value = db.Column(String(50), nullable=True)
    probe_id = db.Column(Integer, ForeignKey("probe.id"), nullable=True)

    def __repr__(self):
        return "<ProbeOption {}>".format(self.choice_id)


class ProbeResponse(db.Model):
    __tablename__ = "probe_response"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    session_id = db.Column(String, nullable=True)
    user_id = db.Column(String, nullable=True)
    value = db.Column(String(50), nullable=True)
    probe_id = db.Column(Integer, ForeignKey("probe.id"), nullable=True)
    actions = db.relationship("Action", backref="probe_response", lazy=True)
    kdmas = db.relationship("KDMA", secondary="probe_response_kdma", lazy="subquery")

    def get_feature_dict(self):
        return {
            "treatment": self.value,
        }

    def get_parent_state(self):
        """
        Returns the state of the parent scenario of the probe so it can be added to the response
        to from a complete TADProbe object. This is different than the probe state which is an indicator
        in the TA1 data of an event that has occurred prior to this question.
        """
        return self.probe.scenario.state

    def __repr__(self):
        return "<ProbeResponse {}>".format(self.value)

    def save(self):
        db.session.add(self)
        db.session.commit()


class Alignment(db.Model):
    __tablename__ = "alignment"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    session_id = db.Column(String, nullable=True)
    scenario_id = db.Column(Integer, ForeignKey("scenario.id"), nullable=True)
    score = db.Column(Float, nullable=True)
    kdmas = db.relationship("KDMA", secondary="alignment_kdma", lazy="subquery")

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<Alignment {}>".format(self.score)


alignment_kdma = db.Table(
    "alignment_kdma",
    db.Column(
        "alignment_id", db.Integer, db.ForeignKey("alignment.id"), primary_key=True
    ),
    db.Column("kdma_id", db.Integer, db.ForeignKey("kdma.id"), primary_key=True),
)


class KDMA(db.Model):
    __tablename__ = "kdma"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    is_alignment = db.Column(Boolean, nullable=True)
    kdma_name = db.Column(String, nullable=True)
    kdma_value = db.Column(Integer, nullable=True)

    def get_feature_dict(self):
        return {
            self.kdma_name: self.kdma_value,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "{} {}".format(self.kdma_name, self.kdma_value)


class Action(db.Model):
    __tablename__ = "action"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String, nullable=True)
    justification = db.Column(String, nullable=True)
    unstructured = db.Column(Text, nullable=True)
    action_type = db.Column(String(50), nullable=True)
    action_description = db.Column(String(50), nullable=True)

    parameters = db.relationship("ActionParameters", backref="action", lazy=True)
    kdmas = db.relationship("KDMA", secondary="action_kdma", lazy="subquery")
    probe_response_id = db.Column(
        Integer, ForeignKey("probe_response.id"), nullable=True
    )
    casualty_id = db.Column(Integer, ForeignKey("casualty.id"), nullable=True)

    def get_feature_dict(self):
        return {
            "action_type": self.action_type,
            # "action_description": self.action_description,
        }

    def apply_treatment(self, treatment_supply):
        action_parameter = ActionParameters(
            parameter_type="treatment",
            parameter_value=treatment_supply,
        )
        self.parameters.append(action_parameter)
        db.session.add(action_parameter)

    def check_all_vitals(self, casualty_id):  # no parameters
        pass

    def check_pulse(self, casualty_id):
        pass

    def check_respiration(self, casualty_id):
        pass

    def direct_mobile_casualties(self):
        pass

    def move_to_evac(self, casualty_id):
        pass

    def sitrep(self, casualty_id=None):
        pass

    def tag_casualty(self, tag_label):
        action_parameter = ActionParameters(
            parameter_type="tag",
            parameter_value=tag_label,
        )
        self.parameters.append(action_parameter)
        db.session.add(action_parameter)

    def __repr__(self):
        return "<Action {}>".format(self.action_type)

    def save(self):
        db.session.add(self)
        db.session.commit()


class ActionParameters(db.Model):
    __tablename__ = "action_parameters"
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = db.Column(String, nullable=True)
    parameter_type = db.Column(String(50), nullable=True)
    parameter_value = db.Column(String(50), nullable=True)
    action_id = db.Column(Integer, ForeignKey("action.id"), nullable=True)

    def get_feature_dict(self):
        return {
            self.parameter_type: self.parameter_value,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<ActionParameters {}>".format(self.parameter_type)


action_kdma = db.Table(
    "action_kdma",
    db.Column("action_id", db.Integer, db.ForeignKey("action.id"), primary_key=True),
    db.Column("kdma_id", db.Integer, db.ForeignKey("kdma.id"), primary_key=True),
)

probe_response_kdma = db.Table(
    "probe_response_kdma",
    db.Column("probe_response_id", db.Integer, db.ForeignKey("probe_response.id")),
    db.Column("kdma_id", db.Integer, db.ForeignKey("kdma.id")),
)
