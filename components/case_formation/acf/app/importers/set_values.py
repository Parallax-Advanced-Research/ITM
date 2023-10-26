from app.probe.models import (
    Probe,
    ProbeOption,
    ProbeResponse,
    KDMA,
    Alignment,
    Action,
    ActionParameters,
)
from app.case.models import Case, CaseBase
from app.scenario.models import Scenario, Threat, Casualty
from app.probe.models import Probe, ProbeOption, ProbeResponse, KDMA, Alignment
from app import db
import yaml
import os
import json

tag_prompts = [
    "How would you tag A?",
    "How would you tag B?",
    "How would you tag C?",
    "How would you tag D?",
    "How would you tag E?",
    "How would you tag F?",
]

tag_names = [
    "casualty-A",
    "casualty-B",
    "casualty-C",
    "casualty-D",
    "casualty-E",
    "casualty-F",
]

tags = ["Green Tag", "Yellow Tag", "Red Tag", "Black Tag"]
labels = ["MINOR", "DELAYED", "IMMEDIATE", "EXPECTANT"]


def add_tags(prompt, casualty_name):
    casebase_id = 2
    for tag, label in zip(tags, labels):
        add_tag(prompt, casualty_name, tag, label, casebase_id)


def add_tag(prompt, casualty_name, tag, label, casebase_id):
    cases = Case.query.filter_by(casebase_id=casebase_id).all()
    for case in cases:
        for scenario in case.scenarios:
            casualties = scenario.casualties
            for probe in scenario.probes:
                if probe.prompt == prompt:
                    casualty = Casualty.query.filter_by(name=casualty_name).first()
                    for response in probe.responses:
                        if response.value == tag and response.actions == []:
                            action = Action(
                                action_type="TAG_CASUALTY",
                                created_by="import",
                            )
                            action.tag_casualty(label)
                            casualty.actions.append(action)
                            casualty.save()
                            response.actions.append(action)
                            db.session.commit()


def add_tourniquet():
    cases = Case.query.filter_by(casebase_id=1).all()
    for case in cases:
        for scenario in case.scenarios:
            for probe in scenario.probes:
                for response in probe.responses:
                    if (
                        response.value
                        == "Place a tourniquet around the left leg to control the bleeding."
                    ):
                        casualty = scenario.casualties[0]
                        action = Action(
                            action_type="APPLY_TREATMENT",
                            created_by="import",
                        )
                        action.apply_treatment("Tourniquet")
                        location_parameter = ActionParameters(
                            parameter_type="location",
                            parameter_value="LEFT_CALF",
                        )
                        action.parameters.append(location_parameter)
                        casualty.actions.append(action)
                        casualty.save()
                        response.actions.append(action)
                        db.session.commit()


def set_session_kdmas():
    data = {}
    with open("data/mvp2_input/MVP2_synthetic_data_150.json") as f:
        data = json.load(f)

    messages = data["messages"]
    for message in messages:
        session_id = message["session_id"]
        message_alignment = message["alignment"]
        kdmas = message_alignment["kdma_values"]

        probe_responses = ProbeResponse.query.filter_by(session_id=session_id).all()
        for probe_response in probe_responses:
            probe_response.kdmas = []
            for kdma in kdmas:
                kdma_value = kdma["value"]
                kdma_name = kdma["kdma"]
                kdma = KDMA(
                    kdma_name=kdma_name,
                    kdma_value=kdma_value,
                    created_by="import",
                )
                probe_response.kdmas.append(kdma)
            probe_response.save()
            db.session.commit()
