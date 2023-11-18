import click
import random

# creates a context so SQLAlchemy can find the app and access the database
from app import create_app
from app.case.models import CaseBase, Case
from app.probe.models import Probe, ProbeResponse
from app.analyze.models import (
    ProbeToAnalyze,
    MonteCarloAnalyzer,
    BayesNetDiagnosisAnalyzer,
    HeuristicRuleAnalyzer,
    EventBasedDiagnosisAnalyzer,
)

app = create_app()
app.app_context().push()


@click.group()
def cli():
    """Manage cases in the database."""
    pass


@cli.command()
def listcasebase():
    case_bases = CaseBase.query.all()
    for case_base in case_bases:
        click.echo(case_base.name)
    """List all cases in the database."""
    click.echo("List cases")


@click.command()
def listcases():
    """List all cases in the database."""
    cases = Case.query.all()
    for case in cases:
        click.echo(case.name)


@click.command()
def listprobes():
    """List all probes in the database."""
    probes = Probe.query.all()
    for probe in probes:
        click.echo(probe.type)


@cli.command()
def randomprobe():
    """Get a random probe for testing"""
    # get casebase id 2
    case = Case.query.filter_by(casebase_id=2).first()
    scenario = case.scenarios[0]
    probes = scenario.probes
    random_probe = random.choice(probes)
    mc = MonteCarloAnalyzer(max_rollouts=1000, max_depth=2)
    click.echo(random_probe.analyze(mc))
    # mc = MonteCarloAnalyzer(max_rollouts=1000, max_depth=2)
    # probe_to_analyze = ProbeToAnalyze(random_probe, mc)
    # metrics = probe_to_analyze.analyze()
    # click.echo(metrics)


@cli.command()
def randomtadprobe():
    """Get a random probe response as a TAD probe for testing"""
    probes = ProbeResponse.query.all()
    random_probe = random.choice(probes)
    click.echo(random_probe.value)


@cli.command()
def analyze():
    """Analyze a probe response"""
    # get casebase id 2

    casebase2 = CaseBase.query.filter_by(id=2).first()
    casebase2_df = casebase2.as_dataframe(feature_as_action=False)


cli.add_command(listcasebase)
cli.add_command(listcases)
cli.add_command(listprobes)
cli.add_command(randomprobe)
cli.add_command(randomtadprobe)

if __name__ == "__main__":
    cli()
