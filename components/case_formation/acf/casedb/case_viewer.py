from app import create_app, db
from app.case.models import Case, CaseBase
from app.probe.models import Probe, ProbeOption, ProbeResponse
from app.scenario.models import Scenario, Threat, Casualty, Vitals, Supply

# from . import cli

app = create_app()
# cli.register(app)


@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "Case": Case,
        "CaseBase": CaseBase,
        "Probe": Probe,
        "ProbeOption": ProbeOption,
        "ProbeResponse": ProbeResponse,
        "Scenario": Scenario,
        "Threat": Threat,
        "Casualty": Casualty,
        "Vitals": Vitals,
        "Supply": Supply,
    }
