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
from app import db

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
            casualty = scenario.case.casualties[0]
            for probe in scenario.probes:
                for response in probe.responses:
                    if (
                        response.value
                        == "Place a tourniquet around the left leg to control the bleeding."
                    ):
                        print(response.value)
                        """
                        action = Action(
                            action_type="APPLY_TREATMENT",
                            created_by="import",
                        )
                        action.apply_treatment("Tourniquet")
                        location_parameter = ActionParameters(
                            parameter_type="location",
                            parameter_value="LEFT_CALF",
                        )
                        casualty.actions.append(action)
                        casualty.save()
                        response.actions.append(action)
                        db.session.commit()
                        """
