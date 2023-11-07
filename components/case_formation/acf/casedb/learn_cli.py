import click

from app import create_app
from app.importers.set_values import *
from app.case.models import CaseBase
from app.learn import (
    data_preprocessing,
    weight_learning,
    create_argument_case,
    xg_boost_learning,
)

# creates a context so SQLAlchemy can find the app and access the database
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
    casebase1 = CaseBase.query.get_or_404(1)  # load casebase from db
    casebase2 = CaseBase.query.get_or_404(2)
    casebase1_df = casebase1.as_ta1dataframe(
        feature_as_action=False
    )  # this returns the action plus parameters as a single concatenated column
    casebase2_df = casebase2.as_dataframe(
        feature_as_action=False
    )  # this returns the action plus parameters as a single concatenated column
    casebase_df_all = pd.concat([casebase2_df, casebase1_df], ignore_index=True)
    casebase_df_all.to_csv(r"app/learn/combined_casebase.csv", index=None, header=True)
    print(casebase_df_all.to_string())

    df_preprocessed = data_preprocessing(casebase_df_all)  # convert to numeric

    # feature_weights = weight_learning(df_preprocessed)  # learn weights with ReliefF
    # print(feature_weights)
    # print("Accuracy when decision is action with parameters")
    # df_argument_case_base = create_argument_case(df_preprocessed, feature_weights)
    # xg_boost_learning(df_preprocessed)

    casebase1_df = casebase1.as_ta1dataframe(
        feature_as_action=True
    )  # this returns the action plus parameters as separate columns
    casebase2_df = casebase2.as_dataframe(
        feature_as_action=True
    )  # this returns the action plus parameters as separate columns
    casebase_df_all = pd.concat([casebase2_df, casebase1_df], ignore_index=True)
    # output the dataframe to a csv file
    casebase_df_all.to_csv(
        r"app/learn/combined_casebase_action.csv", index=None, header=True
    )
    print(casebase_df_all.to_string())

    # df_preprocessed = data_preprocessing(casebase_df_all)  # convert to numeric
    # feature_weights = weight_learning(df_preprocessed)
    # print(feature_weights)
    # print("Accuracy when decision is action only")
    # df_argument_case_base = create_argument_case(df_preprocessed, feature_weights)
    # other way to learn weights
    # xg_boost_learning(df_preprocessed)


@click.command()
def showcases():
    """Show cases."""
    click.echo("Showing cases")


cli.add_command(learnweights)
cli.add_command(learnall)

if __name__ == "__main__":
    cli()
