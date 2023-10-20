import click

from app import create_app
from app.importers.yaml_importer import YAMLImporter
from app.importers.response_importer import ResponseImporter
from app.util import delete_cases, delete_all

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


# can't have underscores in command names
cli.add_command(importyaml)
cli.add_command(importresponses)
cli.add_command(importyamldir)
cli.add_command(deleteresponses)
cli.add_command(deletecases)
cli.add_command(deleteall)

if __name__ == "__main__":
    cli()
