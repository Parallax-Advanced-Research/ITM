from dataclasses import dataclass
import os
from pathlib import Path

import streamlit as st
import pandas as pd
import pickle as pkl
import os.path as osp
import sys


if osp.abspath('.') not in sys.path:
    sys.path.append(osp.abspath('.'))
import domain
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Metric, Casualty, Supply
from components.decision_analyzer.monte_carlo.medsim.smol.smol_oracle import INJURY_UPDATE, DAMAGE_PER_SECOND
from components.probe_dumper.probe_dumper import DUMP_PATH
from domain.internal import Decision

UNKNOWN_NUMBER = -12.34
UNKOWN_STRING = "--"


def _get_casualty_from_decision(decision, div_text=False):
    casualty = None
    if isinstance(decision, str):
        return 'NA'
    param_dict = decision.value.params
    if not div_text:
        return casualty if 'casualty' not in param_dict.keys() else param_dict['casualty']
    else:
        if 'casualty' not in param_dict.keys():
            return None
        retstr = '''<div title=\"%s\">%s</div>''' % ('Random hovertext', param_dict['casualty'])
        return retstr


def _get_params_from_decision(decision):
    additional = 'None'
    if isinstance(decision, str):
        return 'NA'
    param_dict = decision.value.params
    retdict = {'Location': None if 'location' not in param_dict.keys() else param_dict['location'],
               'Treatment': None if 'treatment' not in param_dict.keys() else param_dict['treatment'],
               'Tag': None if 'category' not in param_dict.keys() else param_dict['category']}
    return retdict


def get_html_decision(decision):
    hoverstring = """%s:, Average Severity: %.2f, Supplies Remaining: %d (%d used), Average Time Used: %d""" % (
        decision.value.name, decision.metrics[Metric.SEVERITY.value].value if Metric.SEVERITY.value in decision.metrics.keys() else -1.0,
        decision.metrics[Metric.SUPPLIES_REMAINING.value].value if Metric.SUPPLIES_REMAINING.value in decision.metrics.keys() else -1.0,
        decision.metrics[Metric.SUPPLIES_USED.value].value if Metric.SUPPLIES_USED.value in decision.metrics.keys() else -1.0,
        decision.metrics[Metric.AVERAGE_TIME_USED.value].value if Metric.AVERAGE_TIME_USED.value in decision.metrics.keys() else -1.0)
    retstr = '''<div title=\"%s\">%s</div>''' % (hoverstring, decision.value.name)
    return retstr


def get_html_justification(justification_list):
    if justification_list[0][Metric.DECISION_JUSTIFICATION_ENGLISH.value] == 'End Scenario not Simulated':
        return {Metric.DAMAGE_PER_SECOND.value: 'End Scenario not Ranked',
                Metric.P_DEATH.value: 'End Scenario not Ranked',
                Metric.AVERAGE_TIME_USED.value: 'Undefined by TA3',
                Metric.P_DEATH_ONEMINLATER.value: 'End Scenario not Ranked'}
    return {Metric.DAMAGE_PER_SECOND.value: justification_list[3][Metric.DECISION_JUSTIFICATION_ENGLISH.value],
            Metric.P_DEATH.value: justification_list[4][Metric.DECISION_JUSTIFICATION_ENGLISH.value],
            Metric.AVERAGE_TIME_USED.value: justification_list[2][Metric.DECISION_JUSTIFICATION_ENGLISH.value],
            Metric.P_DEATH_ONEMINLATER.value: justification_list[5][Metric.DECISION_JUSTIFICATION_ENGLISH.value]}


def htmlify_casualty(casualty: Casualty):
    if len(casualty.injuries) == 0:
        return '|%s| None | N/A | N/A| N/A | N/A| N/A |\n' % casualty.id
    lines = ''
    for injury in casualty.injuries:
        injury_effect = INJURY_UPDATE[injury.name]
        bleed = f'{injury_effect.bleeding_effect} ({DAMAGE_PER_SECOND[injury_effect.bleeding_effect]})'
        breath = f'{injury_effect.breathing_effect} ({DAMAGE_PER_SECOND[injury_effect.breathing_effect]})'
        burn = f'{injury_effect.burning_effect} ({DAMAGE_PER_SECOND[injury_effect.burning_effect]})'
        lines += '|%s|%s|%s|%s|%s|%s|%s|\n' % (casualty.id, injury.name, injury.location, injury.treated, bleed, breath, burn)
    return lines


def get_casualty_table(scenario):
    header = '''|Character| Injury | Location| Treated| Bleed| Breath| Burn|
|---|---|---|---|---|---|---|\n'''
    lines = ''
    for casualty in scenario.casualties:
        lines += htmlify_casualty(casualty)
    return '''%s%s<hr>''' % (header, lines)


def htmlify_supply(supply: Supply, make_pink=False):
    if make_pink:
        html_sup = '''|<font color="#FF69B4">%s</font>|<font color="#FF69B4">%d</font>|\n''' % (supply.type, supply.quantity - 1)
    else:
        html_sup = '''|%s|%d|\n''' % (supply.type, supply.quantity)
    return html_sup


def get_supplies_table(scenario, sup_used):
    header = '''|Supplies| Quantity|
|---|---|\n'''
    lines = ''
    for supply in scenario.supplies:
        if supply.type == sup_used:
            lines += htmlify_supply(supply, True)
        else:
            lines += htmlify_supply(supply)
    return '''%s%s<hr>''' % (header, lines)


def htmlify_action(idx, action_performed, make_pink=False):
    if make_pink:
        action_string = '''|<font color="#FF69B4">%s</font>|<font color="#FF69B4">%d</font>|\n''' % (action_performed, idx + 1)
    else:
        action_string = '''|%s|%d|\n''' % (action_performed, idx + 1)
    return action_string


def get_previous_actions(scenario):
    header = '''|Decision|Decision Number|
|---|---|\n'''
    lines = ''
    num_actions = len(scenario.actions_performed)
    flipped_list = reversed(scenario.actions_performed)
    for idx, action_performed in enumerate(flipped_list):
        pink = idx == 0
        lines += htmlify_action(num_actions - idx - 1, action_performed, pink)
    return '''%s%s\n''' % (header, lines)


def read_saved_scenarios():
    scenarios_run = os.listdir(DUMP_PATH)
    scenarios_run = [osp.join(DUMP_PATH, x) for x in scenarios_run if 'pkl' in x]
    scenario_hash = {}

    for sr in scenarios_run:
        scenario_hash[Path(sr).stem] = pkl.load(file=open(sr, mode='rb'))
    return scenario_hash


def construct_environment_table_helper(environment: dict):
    header = '''|Environment Variable| State|
|---|---|\n'''
    for env, state in environment.items():
        if type(state) is not list:
            header += '|%s|%s|\n' % (env, str(state).strip())
        else:
            all_tables = ''
            for x in state:
                table = '<table> <tbody>'
                for s in x:
                    row = f'<tr>  <td>{s}</td> <td>{x[s]}</td>  </tr>'
                    table += row
                table += ' </tbody>  </table> <br>'
                all_tables += table
            header += '|%s|%s|\n' % (env, all_tables)
    return header


def construct_environment_table(enviornment: dict):
    if len(enviornment) == 2:
        keys = list(enviornment)
        env1 = enviornment[keys[0]]
        env2 = enviornment[keys[1]]
        sim_env = construct_environment_table_helper(env1)
        dec_env = construct_environment_table_helper(env2)
        return sim_env, dec_env
    else:
        env = construct_environment_table_helper(environment)
        return env, None


def get_hra_strategy(decision):
    metrics, justifications = decision.metrics, decision.justifications
    selected_strategy = "None"
    selected_justification = "No justification provided"
    hra_strategies = ['Take-The-Best Priority', 'Exhaustive Priority', 'Tallying Priority',
                      'Satisfactory Priority', 'One-Bounce Priority']
    for hra_s in hra_strategies:
        if metrics[hra_s].value:
            selected_strategy = hra_s
            break
    return selected_strategy, selected_justification


def _make_display_name(metric_name):
    return METRIC_DISPLAY_NAME_DESCRIPTION[metric_name][0].replace('<br>', ' ') + ' ' + METRIC_DISPLAY_NAME_DESCRIPTION[metric_name][3]

def _reset_chosen_metrics_to_false(chosen_metrics):
    for choice in chosen_metrics:
        choice.chosen_metric = False

def _calc_group_names_count(sorted_metrics):
    groups = {}
    for metric in sorted_metrics:
        if metric.chosen_metric:
            group_name = METRIC_DISPLAY_NAME_DESCRIPTION[metric.name][3]
            if groups.get(group_name, None) is None:
                groups[group_name] = 1
            else:
                groups[group_name] = groups[group_name] + 1
    return groups


def construct_decision_table(analysis_df, metric_choices, sort_metric):
    sort_func = None
    # create the sort func, a lambda directing to chosen metric in dataframe
    for m_c in metric_choices:
        if m_c.chosen_metric:
            display_name = _make_display_name(m_c.name)
            if display_name == sort_metric:
                if display_name == 'HRA Strategy':
                    sort_func = lambda x: get_hra_strategy(x)[0] if 'HRA Strategy' in x.metrics.keys() else x.id_
                else:
                    sort_func = lambda x: x.metrics[m_c.name].value if m_c.name in x.metrics.keys() else 0.0
                break
    # sort the dataframe
    sorted_df = sorted(analysis_df, key=sort_func)

    # sort metric_choices by grouping
    sorted_metric_choices = sorted(metric_choices, key=lambda x: x.group_name)
    group_names_counts = _calc_group_names_count(sorted_metric_choices)

    table_full_html = "<table>"

    # header for groupings
    # constant metrics
    table_full_html += '<tr style="text-align: center"> <th colspan="5"> </th>'
    # dynamic metrics
    for group in group_names_counts.items():
        table_full_html += f'<th colspan="{group[1]}"> {group[0]} </th>'
    table_full_html += '</tr>'  # end of group headings

    # header
    table_full_html += '<tr> <th>Decision</th> <th>Character</th> <th>Location</th> <th>Treatment</th> <th>Tag</th>'
    for m_c in sorted_metric_choices:
        if m_c.chosen_metric:
            display_name = METRIC_DISPLAY_NAME_DESCRIPTION[m_c.name][0]
            table_full_html += f"""<th> <div title='{METRIC_DISPLAY_NAME_DESCRIPTION[m_c.name][1]}'> {display_name} </div> </th>"""
    table_full_html += '</tr>'  # end of headings

    # table data
    supply_used = None
    for decision in sorted_df:
        pink_style = ''
        # get the supply if one was used
        if decision.selected:
            pink_style = 'style="color: #FF69B4"'
            try:
                supply_used = decision.value.params['treatment']
            except:
                supply_used = None

        # always same stuff
        casualty = _get_casualty_from_decision(decision)
        additional = _get_params_from_decision(decision)
        decision_html_string = get_html_decision(decision)
        table_full_html += f"""<tr {pink_style}> <td>{decision_html_string}</td> <td>{casualty}</td> <td>{additional['Location']}</td> <td>{additional['Treatment']}</td> <td>{additional['Tag']}</td>"""

        justifications = get_html_justification(decision.justifications)

        # dynamic stuff
        for m_c in sorted_metric_choices:
            if m_c.chosen_metric:
                if m_c.name == 'HRA Strategy':
                    strat_selected, strat_justification = get_hra_strategy(decision)
                    table_full_html += f"""<td {pink_style}> <div title='{strat_justification}'> {strat_selected} </div> </td>"""
                else:
                    try:
                        just_english = justifications[m_c.name].split('is')[-1]
                    except:
                        just_english = 'No justification given'
                    metric = decision.metrics[m_c.name].value if m_c.name in decision.metrics.keys() else UNKNOWN_NUMBER
                    display_metric = METRIC_DISPLAY_NAME_DESCRIPTION[m_c.name][2].format(metric + 0) if metric != UNKNOWN_NUMBER else UNKOWN_STRING
                    table_full_html += f"""<td {pink_style}> <div title='{just_english}'> {display_metric} </div> </td>"""

        table_full_html += '</tr>'  # end of data row

    table_full_html += '</table>'
    return table_full_html, supply_used

# This should be the only spot that is needed to be changed when adding a new metric
#  This is a dictionary with the key being the same as in the decision.metric, followed by a tuple that contains
#  - the way it should be displayed (use <br> for where the desired break is in the name for the table
#  - the description of the metric (hover over the name in the table and a tool tip will appear)
#  - formatting for the number (percentage, leading 0s, number of decimals, etc)
#  - what group they are a part of BNDA, MCA, ect
METRIC_DISPLAY_NAME_DESCRIPTION = {
    'pDeath': ('P(Death)', 'Posterior probability of death with no action', '{:.2%}', 'BNDA'),
    'pPain': ('P(Pain)', 'Posterior probability of severe pain', '{:.2%}', 'BNDA'),
    'pBrainInjury': ('P(Brain<br>Injury)', 'Posterior probability of a brain injury', '{:.2%}', 'BNDA'),
    'pAirwayBlocked': ('P(Airway<br>Blocked)', 'Posterior probability of airway blockage', '{:.2%}', 'BNDA'),
    'pInternalBleeding': ('P(Internal<br>Bleeding)', 'Posterior probability of internal bleeding', '{:.2%}', 'BNDA'),
    'pExternalBleeding': ('P(External<br>Bleeding)', 'Posterior probability of external bleeding', '{:.2%}', 'BNDA'),
    'SEVERITY': ('Total<br>Severity', 'Sum of all Severities for all Injuries for all Casualties', '{:.0f}', ''),
    'SUPPLIES_REMAINING': ('Supplies<br>Remaining', 'Supplies remaining', '{:.0f}', ''),
    'AVERAGE_TIME_USED': ('Time', 'Average time used in action', '{:.0f}', 'MCA'),
    'DAMAGE_PER_SECOND': ('Deterioration<br>per second', 'Blood loss ml/sec + lung hp loss/sec + burn shock/second for ALL casualties', '{:.0f}', 'MCA'),
    'MEDSIM_P_DEATH': ('P(Death)', 'Medical simulator probability at least one patient bleeds out, dies of burn shock or asphyxiates from action', '{:.2%}', 'MCA'),
    'MEDSIM_P_DEATH_ONE_MIN_LATER': ('P(Death)<br> + 60s', 'Probability of death after one minute of inactivity after action performed', '{:.2%}', 'MCA'),
    'SEVERITY_CHANGE': ('Severity<br>Change', 'Change in severity from previous state normalized for time.', '{:.2f}', ''),
    'SUPPLIES_USED': ('Supplies<br>Used', 'Supplies used in between current state and projected state', '{:.0f}', ''),
    'ACTION_TARGET_SEVERITY': ('Target<br>Severity', 'The severity of the target', '{:.1f}', ''),
    'ACTION_TARGET_SEVERITY_CHANGE': ('Target<br>Severity<br>Change', 'how much the target of the actions severity changes', '{:.1f}', ''),
    'SEVEREST_SEVERITY': ('Severest<br>Severity', 'what the most severe targets severity is', '{:.1f}', ''),
    'SEVEREST_SEVERITY_CHANGE': ('Severest<br>Severity<br>Change', 'What the change in the severest severity target is', '{:.1f}', ''),
    'All Predictors': ('All<br>Predictors', 'ALL....Predictors.', '{:.1f}', ''),  # thought we were skipping this not sure why it is here
    'entropy': ('Entropy', 'H[entire bayesian network | observations]', '{:.3f}', 'BNDA'),
    'entropyDeath': ('Entropy<br>Death', 'H[death | observations]', '{:.3f}', 'BNDA'),
    'WEIGHTED_RESOURCE_SCORE': ('Weighted<br>Resource', 'More lifesaving items are weighted heavier', '{:.0f}', 'MCA'),
    'SMOL_MEDICAL_SOUNDNESS': ('Medical<br>Soundness', 'Harmonic Mean of Damage Per Second and Probability Death', '{:.0f}', 'MCA'),
    'INFORMATION_GAINED': ('Information<br>Gained', 'How much information is gained by the action', '{:.0f}', 'MCA'),
    'HRA Strategy': ('HRA<br>Strategy', 'Strategies include Take the Best, Exhaustive, Tallying, Satisfactory, and One Bounce', '', 'HRA')
}


@dataclass
class ChosenMetric:
    name: str
    chosen_metric: bool
    group_name: str


def make_checkboxes_list_for_metrics(analysis_df):
    ignore_metrics = ['origins', 'NONDETERMINISM', 'All Predictors', 'Take-The-Best Priority',
                      'Exhaustive Priority', 'Tallying Priority', 'Satisfactory Priority', 'One-Bounce Priority']
    allowed_metrics: list[ChosenMetric] = []

    metrics = []
    for row in analysis_df:
        if len(row.metrics) > len(metrics):
            metrics = row.metrics

    for metric in metrics:
        if metric not in ignore_metrics:
            allowed_metrics.append(ChosenMetric(metric, False, METRIC_DISPLAY_NAME_DESCRIPTION[metric][3]))
    return allowed_metrics


if __name__ == '__main__':
    params = st.query_params

    mc_only = True  # while HRA/BN/EBD are finished

    st.set_page_config(page_title='ITM Decision Viewer', page_icon=':fire:', layout='wide')
    scenario_pkls = read_saved_scenarios()

    # get the scen from url or drop down
    if params.get('scen', None) is not None:
        scen = params['scen'].split('-')[:-1]
        scen = '-'.join(scen)
        chosen_scenario = scen
    else:
        chosen_scenario = st.selectbox(label="Choose a scenario", options=scenario_pkls)

    # get the decision
    num_decisions = [i + 1 for i in range(len(scenario_pkls[chosen_scenario].decisions_presented))]
    # have to check again, for the probe number, need the total number of decision from the scen though
    if params.get('scen', None) is not None:
        probe = params['scen'].split('-')[-1]
        chosen_decision = int(probe) + 1  # adding 1 for display
    else:
        chosen_decision = st.selectbox(label="Choose a decision", options=num_decisions)

    # get the scen
    analysis_df = scenario_pkls[chosen_scenario].decisions_presented[chosen_decision - 1]

    # stuff for metrics selection
    # gather all options
    metric_choices = make_checkboxes_list_for_metrics(analysis_df)
    options_chosen = st.multiselect('Select metrics to display', [_make_display_name(x.name) for x in metric_choices])
    # update metric_choices with which metrics were chosen
    _reset_chosen_metrics_to_false(metric_choices)
    for option in options_chosen:
        for choice in metric_choices:
            if _make_display_name(choice.name) == option:
                choice.chosen_metric = True

    # sort options depends on metric choices so needs to be after
    # it will be done using display name, so will need to index the sort functions by display name
    # kinda sad, but not sure how to get around it right now
    sort_by = st.selectbox(label="Sort by", options=[_make_display_name(x.name) for x in metric_choices if x.chosen_metric])

    st.header("""Scenario: %s""" % chosen_scenario.split('\\')[-1])
    st.subheader("""Probe %d/%d""" % (chosen_decision, len(num_decisions)))

    state = scenario_pkls[chosen_scenario].states[chosen_decision - 1]
    environment = scenario_pkls[chosen_scenario].environments[chosen_decision - 1]
    environment_table_1, environment_table_2 = construct_environment_table(environment)
    if environment_table_2 is not None:
        notes = '##### CONTEXT: '
        notes += environment['decision_environment']['unstructured']
        st.markdown(notes)
    st.caption("The pink decision in the table below is the chosen decision.")

    decision_table_html, supply_used = construct_decision_table(analysis_df, metric_choices, sort_metric=sort_by)
    casualty_html = get_casualty_table(state)
    supply_html = get_supplies_table(state, supply_used)
    previous_action_table = get_previous_actions(state)
    st.markdown(decision_table_html, unsafe_allow_html=True)

    col0, col1, col2, col3 = st.columns(4)
    with col0:
        st.header('Environment')
        if environment_table_2 is None:
            st.markdown(environment_table_1, unsafe_allow_html=True)
        else:
            st.subheader('Simulation')
            st.markdown(environment_table_1, unsafe_allow_html=True)
            st.subheader('Decision')
            st.markdown(environment_table_2, unsafe_allow_html=True)
    with col1:
        st.header('Supplies')
        if supply_used is not None:
            st.caption("""The <font color="#FF69B4">pink supply</font> in the table below is the used supply. Count of supply has been adjusted""",
                       unsafe_allow_html=True)
        st.markdown(supply_html, unsafe_allow_html=True)
    with col2:
        st.header('Previous Action')
        st.markdown(previous_action_table, unsafe_allow_html=True)
    with col3:
        st.header('Characters')
        st.markdown(casualty_html, unsafe_allow_html=True)

