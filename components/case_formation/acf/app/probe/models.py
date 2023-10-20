from app import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text


class Probe(db.Model):
    __tablename__ = "probe"
    id = db.Column(Integer, primary_key=True)
    probe_id = db.Column(String, nullable=True)
    type = db.Column(String(50), nullable=True)
    prompt = db.Column(String(50), nullable=True)
    state = db.Column(String(50), nullable=True)
    time_stamp = db.Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    options = db.relationship("ProbeOption", backref="probe", lazy=True)
    responses = db.relationship("ProbeResponse", backref="probe", lazy=True)
    scenario_id = db.Column(Integer, ForeignKey("scenario.id"), nullable=True)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<Probe {}>".format(self.probe_id)


class ProbeOption(db.Model):
    __tablename__ = "probe_option"
    id = db.Column(Integer, primary_key=True)
    choice_id = db.Column(String, nullable=True)
    value = db.Column(String(50), nullable=True)
    probe_id = db.Column(Integer, ForeignKey("probe.id"), nullable=True)
    created_by = db.Column(String(50), nullable=True)

    def __repr__(self):
        return "<ProbeOption {}>".format(self.choice_id)


class ProbeResponse(db.Model):
    __tablename__ = "probe_response"
    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(String, nullable=True)
    value = db.Column(String(50), nullable=True)
    probe_id = db.Column(Integer, ForeignKey("probe.id"), nullable=True)
    created_by = db.Column(String(50), nullable=True)
    time_stamp = db.Column(DateTime, nullable=False, default=datetime.utcnow)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<ProbeResponse {}>".format(self.value)
