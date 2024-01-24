import os

import streamlit as st
import pandas as pd
import pickle as pkl
import os.path as osp
import sys


if osp.abspath('.') not in sys.path:
    sys.path.append(osp.abspath('.'))
import domain
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Metric, metric_description_hash
from components.probe_dumper.probe_dumper import DUMP_PATH
from domain.mvp.mvp_state import Casualty, Supply
from domain.internal import Decision

UNKNOWN_NUMBER = -12.34
UNKOWN_STRING = "Not Calculated"


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


def make_html_table_header(demo_mode):
    if not demo_mode:
        return '''| Decision         | Casualty     | Location | Treatment  | Tag | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |
|------------------|--------------|----------|------------|-------|----------|-------------------|-----|---|--|--|--|--|--|--|--|\n''' % (
            """<div title=\"%s\">MCA<br>Time</div>""" % metric_description_hash[Metric.AVERAGE_TIME_USED.value],
            """<div title=\"%s\">MCA<br>Deterioration<br>per second</div>""" % metric_description_hash[
                Metric.DAMAGE_PER_SECOND.value],
            """<div title=\"%s\">MCA<br>P(Death)</div>""" % metric_description_hash[Metric.P_DEATH.value],
            """<div title=\"%s\">MCA<br>P(Death) + 60s</div>""" % metric_description_hash[
                Metric.P_DEATH_ONEMINLATER.value],
            """<div title=\"%s\">HRA<br>Strategy</div>""" % """Strategies include Take the Best, Exhaustive, Tallying, Satisfactory, and One Bounce""",
            """<div title=\"%s\">BNDA<br>P(Death)</div>""" % """Posterior probability of death with no action""",
            """<div title=\"%s\">BNDA<br>P(Pain)</div>""" % """Posterior probability of severe pain""",
            """<div title=\"%s\">BNDA<br>P(BrainInjury)</div>""" % """Posterior probability of a brain injury""",
            """<div title=\"%s\">BNDA<br>P(AirwayBlocked)</div>""" % """Posterior probability of airway blockage""",
            """<div title=\"%s\">BNDA<br>P(InternalBleeding)</div>""" % """Posterior probability of internal bleeding""",
            """<div title=\"%s\">BNDA<br>P(ExternalBleeding)</div>""" % """Posterior probability of external bleeding"""
        )
    return '''| Decision         | Casualty     | Location | Treatment  | Tag | Probability Death | P(Death) Justification |
|------------------|--------------|----------|------------|-------|-------------------|-----|\n'''


def select_proper_justification(justification_list, metric):
    for justification in justification_list:
        eng_justification = justification[Metric.DECISION_JUSTIFICATION_ENGLISH.value]
        metric_name = eng_justification.split(' ')[0]
        if metric == metric_name:
            return eng_justification
    return 'No justification found for %s' % metric


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


def get_html_line(decision, demo_mode):
    casualty = _get_casualty_from_decision(decision,)
    additional = _get_params_from_decision(decision)
    justifications = get_html_justification(decision.justifications)
    time_english = justifications[Metric.AVERAGE_TIME_USED.value].split('is')[-1]
    if casualty is None:
        pass
    medsim_pdeath_english = justifications[Metric.P_DEATH.value].split('is')[-1]
    dps_english = justifications[Metric.DAMAGE_PER_SECOND.value].split('is')[-1]
    death_60s_english = justifications[Metric.P_DEATH_ONEMINLATER.value].split('is')[-1]
    decision_html_string = get_html_decision(decision)
    hra_strategy_selector = get_hra_strategy(decision)
    is_pink = decision.selected
    no_just = "No justification given"
    if not demo_mode:
        base_string = '|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n'
        if is_pink:
            base_string = base_string.replace("""%""", """<font color="#FF69B4">%""")
            base_string = base_string.replace("""s""", """s</font>""")

        return base_string % (decision_html_string, casualty, additional['Location'],
                                               additional['Treatment'], additional['Tag'],
                                               '''<div title=\"%s\">%.1f</div>''' % (time_english, decision.metrics[Metric.AVERAGE_TIME_USED.value].value) if Metric.AVERAGE_TIME_USED.value in decision.metrics.keys() else UNKNOWN_NUMBER,
                                               '''<div title=\"%s\">%.2f</div>''' % (dps_english, decision.metrics[Metric.DAMAGE_PER_SECOND.value].value) if Metric.DAMAGE_PER_SECOND.value in decision.metrics.keys() else UNKNOWN_NUMBER,
                                               '''<div title=\"%s\">%.2f %%</div>''' % (medsim_pdeath_english, 100 * decision.metrics[Metric.P_DEATH.value].value) if Metric.P_DEATH.value in decision.metrics.keys() else UNKNOWN_NUMBER,
                                               '''<div title=\"%s\">%.2f %%</div>''' % (death_60s_english,  100 * decision.metrics[Metric.P_DEATH_ONEMINLATER.value].value) if Metric.P_DEATH_ONEMINLATER.value in decision.metrics.keys() else UNKNOWN_NUMBER,
                                               '''<div title=\"%s\">%s</div>''' % (hra_strategy_selector[1],
                                                                                   hra_strategy_selector[0]),

                              '''<div title=\"%s\">%.2f %%</div>''' % (no_just, 100 * decision.metrics['pDeath'].value if 'pDeath' in decision.metrics.keys() else UNKNOWN_NUMBER),
                              '''<div title=\"%s\">%.2f %%</div>''' % (no_just, 100 * decision.metrics['pPain'].value if 'pPain' in decision.metrics.keys() else UNKNOWN_NUMBER),
                              '''<div title=\"%s\">%.2f %%</div>''' % (no_just, 100 * decision.metrics['pBrainInjury'].value if 'pBrainInjury' in decision.metrics.keys() else UNKNOWN_NUMBER),
                              '''<div title=\"%s\">%.2f %%</div>''' % (no_just, 100 * decision.metrics['pAirwayBlocked'].value if 'pAirwayBlocked' in decision.metrics.keys() else UNKNOWN_NUMBER),
                              '''<div title=\"%s\">%.2f %%</div>''' % (no_just, 100 * decision.metrics['pInternalBleeding'].value if 'pInternalBleeding' in decision.metrics.keys() else UNKNOWN_NUMBER),
                              '''<div title=\"%s\">%.2f %%</div>''' % (no_just, 100 * decision.metrics['pExternalBleeding'].value if 'pExternalBleeding' in decision.metrics.keys() else UNKNOWN_NUMBER)
                              )
    else:
        base_string = '|%s|%s|%s|%s|%s|%s|%s|\n'
        return base_string % (decision_html_string, casualty, additional['Location'], additional['Treatment'],
                              additional['Tag'], '''<div title=\"%s\">%.2f</div>''' % (medsim_pdeath_english,
                            decision.metrics[Metric.P_DEATH.value].value) if Metric.P_DEATH.value in decision.metrics.keys() else -1.0,
                            select_proper_justification(decision.justifications, Metric.P_DEATH.value))


def get_html_decision(decision):
    hoverstring = """%s:, Average Severity: %.2f, Supplies Remaining: %d (%d used), Average Time Used: %d""" % (
        decision.value.name, decision.metrics[Metric.SEVERITY.value].value if Metric.SEVERITY.value in decision.metrics.keys() else -1.0,
        decision.metrics[Metric.SUPPLIES_REMAINING.value].value if Metric.SUPPLIES_REMAINING.value in decision.metrics.keys() else -1.0,
        decision.metrics[Metric.SUPPLIES_USED.value].value if Metric.SUPPLIES_USED.value in decision.metrics.keys() else -1.0,
        decision.metrics[Metric.AVERAGE_TIME_USED.value].value if Metric.AVERAGE_TIME_USED.value in decision.metrics.keys() else -1.0)
    retstr = '''<div title=\"%s\">%s</div>''' % (hoverstring, decision.value.name)
    return retstr


def construct_decision_table(analysis_df, demo_mode=False, sort_metric='Time'):
    table_header = make_html_table_header(demo_mode)
    lines = ""
    sort_funcs = {
        'Time': lambda x: x.metrics[Metric.AVERAGE_TIME_USED.value].value if Metric.AVERAGE_TIME_USED.value in x.metrics.keys() else x.id_,
        'Probability Death': lambda x: x.metrics[Metric.P_DEATH.value].value if Metric.P_DEATH.value in x.metrics.keys() else x.id_,
        'Deterioration': lambda x: x.metrics[Metric.DAMAGE_PER_SECOND.value].value if Metric.DAMAGE_PER_SECOND.value in x.metrics.keys() else x.id_,
        'HRA Strategy': lambda x: get_hra_strategy(x)[0] if 'HRA Strategy' in x.metrics.keys() else x.id_,
        'P(Death) (Bayes)': lambda x: x.metrics['pDeath'].value if 'pDeath' in x.metrics.keys() else 0.0,
        'P(Pain) (Bayes)': lambda x: x.metrics['pPain'].value if 'pDeath' in x.metrics.keys() else 0.0,
        'P(BI) (Bayes)': lambda x: x.metrics['pBrainInjury'].value if 'pBrainInjury' in x.metrics.keys() else 0.0,
        'P(Airway Blocked) (Bayes)': lambda x: x.metrics['pAirwayBlocked'].value if 'pAirwayBlocked' in x.metrics.keys() else 0.0,
        'P(Internal Bleeding) (Bayes)': lambda x: x.metrics['pInternalBleeding'].value if 'pInternalBleeding' in x.metrics.keys() else 0.0,
        'P(External Bleeding) (Bayes)': lambda x: x.metrics['pExternalBleeding'].value if 'pExternalBleeding' in x.metrics.keys() else 0.0,
        'Casualty': lambda x: x.value.params['casualty'] if 'casualty' in x.value.params else x.id_

    }
    sorted_df = sorted(analysis_df, key=sort_funcs[sort_metric])
    for decision in sorted_df:
        raw = get_html_line(decision, demo_mode)
        fixed = raw.replace(str(UNKNOWN_NUMBER), UNKOWN_STRING)
        lines += fixed
    full_html = table_header + lines + '<hr>'
    return full_html


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
        scenario_hash[sr.split('.')[0].split('/')[-1]] = pkl.load(file=open(sr, mode='rb'))
    return scenario_hash


def url_scen_helper(param):
    convert_scens = {
        'adept': "components\probe_dumper\\tmp\\adept-september-demo-scenario-1",
        'enemy': 'components\probe_dumper\\tmp\enemy-dying',
        'simple': 'components\probe_dumper\\tmp\simple',
        'soar': 'components\probe_dumper\tmp\soartech-september-demo-scenario-1',
        'tmnt': 'components\probe_dumper\\tmp\\tmnt',
        'vip': 'components\probe_dumper\\tmp\\vip'
    }
    return convert_scens[param]


def url_decision_checker(param, num_dec):
    if 0 < param <= num_dec:
        return param
    else:
        return 1  # defaulting to first decision if param is bad


if __name__ == '__main__':
    params = st.experimental_get_query_params()

    st.set_page_config(page_title='ITM Decision Viewer', page_icon=':fire:', layout='wide')
    scenario_pkls = read_saved_scenarios()
    sort_options = ['Time', 'Probability Death', 'Deterioration', 'Casualty', 'HRA Strategy', 'P(Death) (Bayes)',
                    'P(Pain) (Bayes)', 'P(BI) (Bayes)', 'P(Airway Blocked) (Bayes)', 'P(Internal Bleeding) (Bayes)',
                    'P(External Bleeding) (Bayes)']
    # with st.sidebar:  # Legal term
    if params.get('scen', None) is not None:
        chosen_scenario = url_scen_helper(params['scen'][0])
    else:
        chosen_scenario = st.selectbox(label="Choose a scenario", options=scenario_pkls)
    num_decisions = [i + 1 for i in range(len(scenario_pkls[chosen_scenario].decisions_presented))]
    if params.get('decision', None) is not None:
        chosen_decision = url_decision_checker(int(params['decision'][0]), len(num_decisions))
    else:
        chosen_decision = st.selectbox(label="Choose a decision", options=num_decisions)
    sort_by = st.selectbox(label="Sort by", options=sort_options)
    st.header("""Scenario: %s""" % chosen_scenario.split('\\')[-1])
    st.subheader("""Decision %d/%d""" % (chosen_decision, len(num_decisions)))
    analysis_df = scenario_pkls[chosen_scenario].decisions_presented[chosen_decision - 1]
    state = scenario_pkls[chosen_scenario].states[chosen_decision - 1]

    demo_mode = False  # Only used once probably to show justifications in table. Leave false.

    decision_table_html = construct_decision_table(analysis_df, demo_mode, sort_metric=sort_by)
    casualty_html = get_casualty_table(state)
    supply_html = get_supplies_table(state)
    previous_action_table = get_previous_actions(state)
    st.markdown(decision_table_html, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.header('Supplies')
        st.markdown(supply_html, unsafe_allow_html=True)
    with col2:
        st.header('Previous Action')
        st.markdown(previous_action_table, unsafe_allow_html=True)
    with col3:
        st.header('Casualties')
        st.markdown(casualty_html, unsafe_allow_html=True)
