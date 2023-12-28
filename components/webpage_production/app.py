import streamlit as st
import pandas as pd
import pickle
import os.path as osp
import sys
import numpy as np
if osp.abspath('.') not in sys.path:
    sys.path.append(osp.abspath('.'))
import domain


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
               'Tag': None if 'tag' not in param_dict.keys() else param_dict['tag']}
    return retdict


def casualty_df_from_state(state) -> pd.DataFrame:
    df = pd.DataFrame()
    return df


def supply_df_from_state(state) -> pd.DataFrame:
    df = pd.DataFrame()
    return df


# def display_mca_analysis(analysis_df, scenario):
#     st.set_page_config(page_title='ITM Decision Viewer', page_icon=':fire:', layout='wide')
#     # st.subheader('Hi Im JT :wave:')
#     # st.title("This page shows stats for itm decisions")
#     # st.write('return 3')
#     decision_df = decisions_to_df(decision_list=analysis_df)
#     decision_df.sort_values(by='Damage Per Second', inplace=True)
#     casualty_df = casualty_df_from_state(scenario)
#     supply_df = supply_df_from_state(scenario)
#     st.markdown(decision_df.to_html(), unsafe_allow_html=True)
#     st.table(casualty_df)
#     st.table(supply_df)


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
                                         '''<div title=\"%s\">%.2f</div>''' % (medsim_pdeath_english, decision.metrics['MEDSIM_P_DEATH'].value),
                                         '''<div title=\"%s\">%.2f</div>''' % (dps_english, decision.metrics['DAMAGE_PER_SECOND'].value))


def get_html_decision(decision):
    hoverstring = """%s:, Average Severity: %.2f, Supplies Remaining: %d (%d used), Average Time Used: %d""" % (decision.value.name, decision.metrics['SEVERITY'].value,
                            decision.metrics['SUPPLIES_USED'].value, decision.metrics['SUPPLIES_REMAINING'].value,
                            decision.metrics['AVERAGE_TIME_USED'].value)
    retstr = '''<div title=\"%s\">%s</div>''' % (hoverstring, decision.value.name)
    return retstr


def construct_decision_table(analysis_df):
    table_header = make_html_table_header()
    lines = ""
    # analysis_df.sort_values(by='Damage Per Second', inplace=True)
    for decision in sorted(analysis_df):
        lines += get_html_line(decision)
    full_html = table_header + lines + '<hr>'
    return full_html


def get_html_justification(justification_list):
    if justification_list[0]['DECISION_JUSTIFICATION_ENGLISH'] == 'End Scenario not Simulated':
        return {'dps': 'End Scenario not Simulated', 'pdeath': 'End Scenario not Simulated'}
    return {'dps': justification_list[3]['DECISION_JUSTIFICATION_ENGLISH'],
            'pdeath': justification_list[4]['DECISION_JUSTIFICATION_ENGLISH']}

def get_casualty_table(scenario):
    return '''|Casualty| Injury | Location| Treated|
|---|---|---|---|
|JT| Blown Knee | Left Knee | False|
<hr>'''


def get_supplies_table(scenario):
    return '''|Supplies| Quantity|
|---|---|
|Heavy Books| 1 |
<hr>'''


def get_environmental_table(scenario):
    return '''|Environmental Factor| Threat|
|---|---|
|Cat| Low|
|Flatulance| Medium|
<hr>'''


if __name__ == '__main__':
    analysis_df = pickle.load(open(osp.join('components', 'webpage_production', 'tmp', 'decisions.pkl'), 'rb'))
    scenario = pickle.load(open(osp.join('components', 'webpage_production', 'tmp', 'state.pkl'), 'rb'))
    st.set_page_config(page_title='ITM Decision Viewer HTML VERSION YEE-HAW', page_icon=':fire:', layout='wide')
    st.title("This page shows stats for itm decisions")
    decision_table_html = construct_decision_table(analysis_df)
    casualty_html = get_casualty_table(scenario)
    supply_html = get_supplies_table(scenario)
    environmental_html = get_environmental_table(scenario)
    st.markdown(decision_table_html, unsafe_allow_html=True)
    st.markdown(casualty_html, unsafe_allow_html=True)
    st.markdown(supply_html, unsafe_allow_html=True)
    st.markdown(environmental_html, unsafe_allow_html=True)
