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
)

app = create_app()
app.app_context().push()


@click.group()
def cli():
    pass


@click.command()
@click.argument("casebase_id", type=click.INT)
def learnweights(casebase_id):
    click.echo("Learning weights")
    """Learn weights for probes."""
    casebase = CaseBase.query.get_or_404(casebase_id)  # load casebase from db
    casebase_df = casebase.as_dataframe()  # return as pandas dataframe
    print(casebase_df.to_string())

    # df_preprocessed = data_preprocessing(casebase_df)  # convert to numeric
    # print(df_preprocessed)

    # feature_weights = weight_learning(df_preprocessed)  # learn weights with ReliefF
    # print(feature_weights)
    # df_argument_case_base = create_argument_case(
    #    df_preprocessed, feature_weights
    # )  # create argument case base and compute accuracy

    # other way to learn weights
    # xg_boost_learning(df_preprocessed)


@click.command()
def learnall():
    click.echo("Learning weights")
    """Learn weights for probes."""

    casebase2 = CaseBase.query.get_or_404(2)

    casebase2_df = casebase2.as_dataframe(feature_as_action=True)

    df_preprocessed = data_preprocessing(casebase2_df)  # convert to numeric
    xg_boost_learning(df_preprocessed)


@click.command()
def showcases():
    """Show cases."""
    click.echo("Showing cases")


cli.add_command(learnweights)
cli.add_command(learnall)

if __name__ == "__main__":
    cli()
