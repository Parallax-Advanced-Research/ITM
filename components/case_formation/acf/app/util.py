from app import db
from app.case.models import Case
from app.probe.models import Probe, ProbeOption, ProbeResponse
from app.scenario.models import Scenario, Casualty, casualty_scenario


# cascade
def delete_cases():
    Case.query.delete()
    db.session.commit()


def delete_probes():
    Probe.query.delete()
    db.session.commit()


def delete_probe_options():
    ProbeOption.query.delete()
    db.session.commit()


def delete_probe_responses():
    ProbeResponse.query.delete()
    db.session.commit()


def delete_scenarios():
    Scenario.query.delete()
    db.session.commit()


def delete_casualties():
    Casualty.query.delete()
    db.session.commit()


def delete_case_scenario():
    # remove all entries from the case_scenario table
    case_scenario.delete()
    db.session.commit()


def delete_casualty_scenario():
    casualty_scenario.delete()
    db.session.commit()


def delete_all():
    delete_cases()
    delete_probes()
    delete_probe_options()
    delete_probe_responses()
    delete_scenarios()
    delete_casualties()
    delete_case_scenario()
    delete_casualty_scenario()
    db.session.commit()
