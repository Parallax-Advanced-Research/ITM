from app import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text


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
