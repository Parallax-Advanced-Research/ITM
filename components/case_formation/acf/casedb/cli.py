import click
import random

# creates a context so SQLAlchemy can find the app and access the database
from app import create_app
from app.case.models import CaseBase, Case
from app.probe.models import Probe, ProbeResponse, MonteCarloAnalyzer

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

    # casebase2 = Case.query.filter_by(casebase_id=2).first()
    # case = Case.query.filter_by(id=1).first()
    # probes = case.scenarios[0].probes
    treatment_probes = Probe.query.filter_by(type="SelectTreatment").all()
    random_probe = random.choice(treatment_probes)
    a = random_probe.analyze()
    click.echo(random_probe.type)
    click.echo(a)


@click.command()
def compare():
    """Compare two probes from different casebases"""
    casebase_1 = CaseBase.query.filter_by(id=1).first()
    casebase_2 = CaseBase.query.filter_by(id=2).first()

    # casebase 1 probe
    casebase_1_case = Case.query.filter_by(casebase_id=1).first()
    casebase_1_probe = casebase_1_case.scenarios[0].probes[0]
    click.echo(casebase_1_probe.analyze())

    casebase_2_case = Case.query.filter_by(casebase_id=2).first()
    casebase_2_probe = casebase_2_case.scenarios[0].probes[0]
    click.echo(casebase_2_probe.analyze())


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
    casebase2_df = casebase2.as_dataframe(feature_as_action=False, do_analysis=True)
    print(casebase2_df.to_string())
    # to csv
    casebase2_df.to_csv("casebase2_with_da.csv")


cli.add_command(listcasebase)
cli.add_command(listcases)
cli.add_command(listprobes)
cli.add_command(randomprobe)
cli.add_command(randomtadprobe)
cli.add_command(analyze)
cli.add_command(compare)

if __name__ == "__main__":
    cli()
