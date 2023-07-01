from dataclasses import asdict
from domain.mvp import MVPState, MVPScenario, MVPDecision, Casualty
from .sim_tools import similarity

TIME_W = 0.5
CASUALTY_W = 1
UNSTRUCTURED_W = 1
VITALS_W = 1
DEMOGRAPHIC_W = 1
STATE_W = 1
PROMPT_W = 1


def casuality_sim(c1: Casualty, c2: Casualty) -> float:
    sim = 0
    tot_wgt = UNSTRUCTURED_W + VITALS_W + DEMOGRAPHIC_W

    v1 = asdict(c1.vitals) if c1.vitals is not None else {}
    v2 = asdict(c2.vitals) if c2.vitals is not None else {}
    d1 = asdict(c1.demographics) if c1.demographics is not None else {}
    d2 = asdict(c2.demographics) if c2.demographics is not None else {}

    sim += UNSTRUCTURED_W * similarity(c1.unstructured, c2.unstructured)
    sim += VITALS_W * similarity(v1, v2)
    sim += DEMOGRAPHIC_W * similarity(d1, d2)

    return sim / tot_wgt


def state_sim(s1: MVPState, s2: MVPState) -> float:
    sim = 0
    tot_wgt = TIME_W + UNSTRUCTURED_W

    sim += TIME_W * similarity(s1.time, s2.time)
    sim += UNSTRUCTURED_W * similarity(s1.unstructured, s2.unstructured)

    num_cas = max(len(s1.casualties), len(s2.casualties))
    for i in range(num_cas):
        if len(s1.casualties) > i and len(s2.casualties) > i:
            sim += CASUALTY_W * casuality_sim(s1.casualties[i], s2.casualties[i])
        tot_wgt += CASUALTY_W

    return sim / tot_wgt


def scen_sim(s1: MVPScenario, s2: MVPScenario) -> float:
    sim = 0
    tot_wgt = STATE_W + PROMPT_W

    sim += STATE_W * state_sim(s1.state, s2.state)
    sim += PROMPT_W * similarity(s1.prompt, s2.prompt)

    return sim / tot_wgt


def decision_sim(d1: MVPDecision, d2: MVPDecision) -> float:
    return similarity(d1.value, d2.value)


def align_sim(a1: list, a2: list) -> float:
    a1d = {kdma['kdma'].lower(): float(kdma['value']) for kdma in a1}
    a2d = {kdma['kdma'].lower(): float(kdma['value']) for kdma in a2}
    return similarity(a1d, a2d)
