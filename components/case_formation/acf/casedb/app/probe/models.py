from app import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text, Float, Boolean
import sys
import importlib

# give access to top level modules
sys.path.append("../../../../") # TODO: fix this hack

import domain.internal as TAD




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
