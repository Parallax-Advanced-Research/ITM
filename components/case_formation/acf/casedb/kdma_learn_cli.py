import click

from app import create_app
from app.importers.yaml_importer import YAMLImporter
from app.importers.response_importer import ResponseImporter
from app.importers.st_response_importer import SoarTechResponseImporter
from app.importers.session_importer import SessionImporter
from app.util import delete_cases, delete_all
from app.importers.set_values import *
from app.case.models import CaseBase
from app.kdma_learn import (
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
def learnkdma():
    click.echo("Learning weights")
    """Learn weights for probes."""
    casebase1 = CaseBase.query.get_or_404(1)  # load casebase from db
    casebase2 = CaseBase.query.get_or_404(2)
    casebase1_df = casebase1.as_ta1dataframe(feature_as_action=False)
    casebase2_df = casebase2.as_dataframe(feature_as_action=False)
    casebase_df_all = pd.concat([casebase2_df, casebase1_df], ignore_index=True)
    print(casebase_df_all.to_string())

    df_preprocessed = data_preprocessing(
        casebase_df_all, "mission"
    )  # convert to numeric
    feature_weights = weight_learning(
        df_preprocessed, "mission"
    )  # learn weights with ReliefF
    print("Accuracy when decision is mission")
    df_argument_case_base = create_argument_case(df_preprocessed, feature_weights)
    # xg_boost_learning(df_preprocessed, "mission")

    df_preprocessed = data_preprocessing(
        casebase_df_all, "denial"
    )  # convert to numeric
    feature_weights = weight_learning(
        df_preprocessed, "denial"
    )  # learn weights with ReliefF
    print("Accuracy when decision is denial")
    df_argument_case_base = create_argument_case(df_preprocessed, feature_weights)
    # xg_boost_learning(df_preprocessed, "denial")

    df_preprocessed = data_preprocessing(
        casebase_df_all, "risktol"
    )  # convert to numeric
    feature_weights = weight_learning(
        df_preprocessed, "risktol"
    )  # learn weights with ReliefF
    print("Accuracy when decision is risktol")
    df_argument_case_base = create_argument_case(df_preprocessed, feature_weights)
    # xg_boost_learning(df_preprocessed, "risktol")

    df_preprocessed = data_preprocessing(
        casebase_df_all, "timeurg"
    )  # convert to numeric
    feature_weights = weight_learning(
        df_preprocessed, "timeurg"
    )  # learn weights with ReliefF
    print("Accuracy when decision is timeurg")
    df_argument_case_base = create_argument_case(df_preprocessed, feature_weights)
    # xg_boost_learning(df_preprocessed, "timeurg")


@click.command()
def showcases():
    """Show cases."""
    click.echo("Showing cases")


cli.add_command(learnkdma)

if __name__ == "__main__":
    cli()
