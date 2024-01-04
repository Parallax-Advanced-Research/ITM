import os

import streamlit as st
import pandas as pd
import pickle as pkl
import os.path as osp
import sys


if osp.abspath('.') not in sys.path:
    sys.path.append(osp.abspath('.'))
import domain
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Metric
from components.probe_dumper.probe_dumper import DUMP_PATH
from domain.mvp.mvp_state import Casualty, Supply
from domain.internal import Decision


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


def casualty_df_from_state(state) -> pd.DataFrame:
    df = pd.DataFrame()
    return df


def supply_df_from_state(state) -> pd.DataFrame:
    df = pd.DataFrame()
    return df


def make_html_table_header():
    return '''| Decision         | Casualty     | Location | Treatment  | Tag | Probability Death | DPS |
|------------------|--------------|----------|------------|-------|-------------------|-----|\n'''


def get_html_line(decision):
    casualty = _get_casualty_from_decision(decision,)
    additional = _get_params_from_decision(decision)
    justifications = get_html_justification(decision.justifications)
    medsim_pdeath_english = justifications['pdeath'].split('is')[-1]
    dps_english = justifications['dps'].split('is')[-1]
    decision_html_string = get_html_decision(decision)
    return '|%s|%s|%s|%s|%s|%s|%s|\n' % (decision_html_string, casualty, additional['Location'],
                                         additional['Treatment'], additional['Tag'],
                                         '''<div title=\"%s\">%.2f</div>''' % (medsim_pdeath_english,
                                                                               decision.metrics[Metric.P_DEATH.value].value) if Metric.P_DEATH.value in decision.metrics.keys() else -1.0,
                                         '''<div title=\"%s\">%.2f</div>''' % (dps_english, decision.metrics[Metric.DAMAGE_PER_SECOND.value].value) if Metric.DAMAGE_PER_SECOND.value in decision.metrics.keys() else -1.0)


def get_html_decision(decision):
    hoverstring = """%s:, Average Severity: %.2f, Supplies Remaining: %d (%d used), Average Time Used: %d""" % (
        decision.value.name, decision.metrics[Metric.SEVERITY.value].value if Metric.SEVERITY.value in decision.metrics.keys() else -1.0,
        decision.metrics[Metric.SUPPLIES_REMAINING.value].value if Metric.SUPPLIES_REMAINING.value in decision.metrics.keys() else -1.0,
        decision.metrics[Metric.SUPPLIES_USED.value].value if Metric.SUPPLIES_USED.value in decision.metrics.keys() else -1.0,
        decision.metrics[Metric.AVERAGE_TIME_USED.value].value if Metric.AVERAGE_TIME_USED.value in decision.metrics.keys() else -1.0)
    retstr = '''<div title=\"%s\">%s</div>''' % (hoverstring, decision.value.name)
    return retstr


def construct_decision_table(analysis_df, sort_metric=Metric.DAMAGE_PER_SECOND.value):
    table_header = make_html_table_header()
    lines = ""
    for decision in sorted(analysis_df):
        lines += get_html_line(decision)
    full_html = table_header + lines + '<hr>'
    return full_html


def sort_decisions_function(decisions: list[Decision], sort_fn: callable):
    pass


def get_html_justification(justification_list):
    if justification_list[0][Metric.DECISION_JUSTIFICATION_ENGLISH.value] == 'End Scenario not Simulated':
        return {'dps': 'End Scenario not Simulated', 'pdeath': 'End Scenario not Simulated'}
    return {'dps': justification_list[3][Metric.DECISION_JUSTIFICATION_ENGLISH.value],
            'pdeath': justification_list[4][Metric.DECISION_JUSTIFICATION_ENGLISH.value]}


def htmlify_casualty(casualty: Casualty):
    if len(casualty.injuries) == 0:
        return '|%s| None | N/A | N/A|\n' % casualty.id
    lines = ''
    for injury in casualty.injuries:
        lines += '|%s|%s|%s|%s|\n' % (casualty.id, injury.name, injury.location, injury.treated)
    return lines


def get_casualty_table(scenario):
    header = '''|Casualty| Injury | Location| Treated|
|---|---|---|---|\n'''
    lines = ''
    for casualty in scenario.casualties:
        lines += htmlify_casualty(casualty)
    return '''%s%s<hr>''' % (header, lines)


def htmlify_supply(supply: Supply):
    return '''|%s|%d|\n''' % (supply.type, supply.quantity)


def get_supplies_table(scenario):
    header = '''|Supplies| Quantity|
|---|---|\n'''
    lines = ''
    for supply in scenario.supplies:
        lines += htmlify_supply(supply)
    return '''%s%s<hr>''' % (header, lines)


def htmlify_action(idx, action_performed):
    return '''|%s|%d|\n''' % (action_performed, idx + 1)


def get_previous_actions(scenario):
    header = '''|Decision|Decision Number|
|---|---|\n'''
    lines = ''
    for idx, action_performed in enumerate(scenario.actions_performed):
        lines += htmlify_action(idx, action_performed)
    return '''%s%s\n''' % (header, lines)


def read_saved_scenarios():
    scenarios_run = os.listdir(DUMP_PATH)
    scenarios_run = [osp.join(DUMP_PATH, x) for x in scenarios_run if 'pkl' in x]
    scenario_hash = {}
    for sr in scenarios_run:
        scenario_hash[sr.split('.')[0].split('/')[-1]] = pkl.load(file=open(sr, mode='rb'))
    return scenario_hash


if __name__ == '__main__':
    st.set_page_config(page_title='ITM Decision Viewer', page_icon=':fire:', layout='wide')
    scenario_pkls = read_saved_scenarios()
    with st.sidebar:  # Legal term
        chosen_scenario = st.selectbox(label="Choose a scenario", options=scenario_pkls)
        num_decisions = [i + 1 for i in range(len(scenario_pkls[chosen_scenario].decisions_presented))]
        chosen_decision = st.selectbox(label="Choose a decision", options=num_decisions)
    st.header("""Scenario: %s""" % chosen_scenario)
    st.subheader("""Decision %d/%d""" % (chosen_decision, len(num_decisions)))
    analysis_df = scenario_pkls[chosen_scenario].decisions_presented[chosen_decision - 1]
    state = scenario_pkls[chosen_scenario].states[chosen_decision - 1]
    decision_table_html = construct_decision_table(analysis_df)
    casualty_html = get_casualty_table(state)
    supply_html = get_supplies_table(state)
    environmental_html = get_previous_actions(state)
    st.markdown(decision_table_html, unsafe_allow_html=True)
    st.markdown(casualty_html, unsafe_allow_html=True)
    st.markdown(supply_html, unsafe_allow_html=True)
    st.markdown(environmental_html, unsafe_allow_html=True)
