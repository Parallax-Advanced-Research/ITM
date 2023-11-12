import click

from app import create_app
from app.importers.yaml_importer import YAMLImporter
from app.importers.response_importer import ResponseImporter
from app.importers.st_response_importer import SoarTechResponseImporter
from app.importers.session_importer import SessionImporter
from app.util import delete_cases, delete_all
from app.importers.set_values import *
from app.case.models import CaseBase
from app.learn import (
    data_preprocessing,
    weight_learning,
    create_argument_case,
    xg_boost_learning,
    svm_learning,
)

app = create_app()
app.app_context().push()


@click.group()
def cli():
    pass


@click.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--casebase", type=click.INT, default=1)
def importyaml(file_path, casebase):
    """Import a YAML Scenario file."""
    click.echo("Importing YAML file from {} to casebase {}".format(file_path, casebase))
    importer = YAMLImporter()
    importer.import_case(file_path, casebase)
    click.echo("Imported YAML file from {} to casebase {}".format(file_path, casebase))


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--casebase", type=click.INT, default=1)
def importyamldir(path, casebase):
    """Import the YAML Scenario files in the given directory if they start with MVP2 and end with .yaml."""
    click.echo("Importing YAML files from {} to casebase {}".format(path, casebase))
    importer = YAMLImporter()
    importer.import_cases(path, casebase)
    click.echo("Imported YAML files from {} to casebase {}".format(path, casebase))


@click.command()
def importresponses():
    importer = ResponseImporter()
    importer.import_data()
    """Import a JSON Response file."""
    click.echo("Importing JSON file")


@click.command()
def importsessions():
    importer = SessionImporter()
    importer.import_data()
    """Import a JSON Session file."""
    click.echo("Importing JSON file")


@click.command()
def deleteresponses():
    """Delete all responses."""
    importer = ResponseImporter()
    importer.delete_responses()
    click.echo("Deleting responses")


@click.command()
def deletecases():
    """Delete all cases."""
    delete_cases()
    click.echo("Deleting cases")


@click.command()
def deleteall():
    """Delete all cases."""
    delete_all()
    click.echo("Deleting all")


@click.command()
def importstresponses():
    """Import ST data."""
    click.echo("Importing ST data")
    importer = SoarTechResponseImporter()
    importer.import_data()


@click.command()
@click.argument("prompt", type=click.STRING)
@click.argument("casualty_name", type=click.STRING)
def settags(prompt, casualty_name):
    """Set tags for probes."""
    click.echo("Setting tags")
    add_tags(prompt, casualty_name)


@click.command()
def applytourniquet():
    """Set tags for probes."""
    click.echo("Setting tags")
    add_tourniquet()


@click.command()
def setkdmas():
    """Set tags for probes."""
    click.echo("Setting tags")
    set_session_kdmas()


@click.command()
@click.argument("casebase_id", type=click.INT)
def nullkdmas(casebase_id):
    "set null kdmas"
    click.echo("Setting alignments")
    set_null_alignment(casebase_id)


@click.command()
def applybandage():
    """Set tags for probes."""
    click.echo("Setting tags")
    add_bandage_ta3()


@click.command()
def selectcas():
    """Set tags for probes."""
    click.echo("Selecting casualties")
    add_select_casualty_responses()


@click.command()
def selectcaskdmas():
    """Set tags for probes."""
    click.echo("Setting kdmas")
    add_select_casualty_kdmas()


@click.command()
def showcases():
    """Show cases."""
    click.echo("Showing cases")


# can't have underscores in command names
cli.add_command(importyaml)
cli.add_command(importresponses)
cli.add_command(importstresponses)
cli.add_command(importyamldir)
cli.add_command(importsessions)
cli.add_command(deleteresponses)
cli.add_command(deletecases)
cli.add_command(deleteall)
cli.add_command(settags)
cli.add_command(applytourniquet)
cli.add_command(setkdmas)
cli.add_command(nullkdmas)
cli.add_command(learnweights)
cli.add_command(applybandage)
# cli.add_command(selectcas)
cli.add_command(selectcaskdmas)

if __name__ == "__main__":
    cli()


# order
# importyamldir
# importyaml
# importresponses
# importstresponses
