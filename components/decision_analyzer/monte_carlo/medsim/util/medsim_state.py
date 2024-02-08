import logging
import numpy as np
from components.decision_analyzer.monte_carlo.mc_sim import MCAction, MCState
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Casualty, Actions, Metric, Supply
from components.decision_analyzer.monte_carlo.medsim.smol.smol_oracle import (calc_prob_bleedout,
                                                                              calc_prob_asphyx,
                                                                              calc_prob_death)
from domain.internal import TADProbe


def get_prob(pvals: list[float]):
    prob = 1.
    for pval in pvals:
        not_occur = 1 - pval
        prob *= not_occur
    final_prob = 1 - prob
    return final_prob  # prob is probability of event not happening


class MedsimState(MCState):
    def __init__(self, casualties: list[Casualty], supplies: list[Supply], time: float, unstructured: str = ''):
        super().__init__()
        self.casualties: list[Casualty] = casualties
        self.supplies: list[Supply] = supplies
        self.unstructured = unstructured
        self.time = time
        self.aid_delay: float = 0.0

    def set_aid_delay(self, probe: TADProbe):
        self.aid_delay = probe.environment['aid_delay'] if probe.environment['aid_delay'] is not None else 0.0

    def __eq__(self, other: 'MedsimState'):
        # fastest checks are lengths
        if len(self.casualties) != len(other.casualties):
            return False
        if len(self.supplies) != len(other.supplies):
            return False

        self_cas_sorted = sorted(self.casualties, key=lambda x: x.id)
        other_cas_sorted = sorted(other.casualties, key=lambda x: x.id)
        if self_cas_sorted != other_cas_sorted:
            return False

        # check supplies next
        self_sup_sorted = sorted(self.supplies, key=lambda x: x.name)
        other_sup_sorted = sorted(other.supplies, key=lambda x: x.name)
        if self_sup_sorted != other_sup_sorted:
            return False

        return True

    def get_num_supplies(self) -> int:
        num_supplies: int = 0
        for supply in self.supplies:
            num_supplies += supply.amount
        return num_supplies

    def get_state_severity(self) -> float:
        severity = 0.
        for cas in self.casualties:
            for inj in cas.injuries:
                severity += inj.severity
        return severity

    def get_state_morbidity(self, generic = True) -> dict[str, float | dict[str, float]]:
        morbidity_dict: dict[str, float] = dict()
        sorted_cas: list[Casualty] = sorted(self.casualties)
        if not len(sorted_cas):  # Assuming at least one else return nada
            return {}
        deathly_person = sorted_cas[-1]
        probability_death = get_prob([cas.prob_death for cas in sorted_cas])
        probability_bleedout = get_prob([cas.prob_bleedout for cas in sorted_cas])
        probability_asphyxia = get_prob([cas.prob_asphyxia for cas in sorted_cas])
        probability_shock = get_prob([cas.prob_shock for cas in sorted_cas])
        tot_blood, lung_loss, burn_loss = 0., 0., 0.
        for cas in sorted_cas:
            tot_blood += sum(inj.blood_lost_ml for inj in cas.injuries)
            lung_loss += sum(inj.breathing_hp_lost for inj in cas.injuries)
            burn_loss += sum(inj.burn_hp_lost for inj in cas.injuries)

        morbidity_dict[Metric.P_DEATH.value] = probability_death
        morbidity_dict[Metric.HIGHEST_P_DEATH.value] = calc_prob_death(deathly_person)
        if not generic:
            morbidity_dict[Metric.P_BLEEDOUT.value] = probability_bleedout
            morbidity_dict[Metric.P_ASPHYXIA.value] = probability_asphyxia
            morbidity_dict[Metric.P_SHOCK.value] = probability_shock
            morbidity_dict[Metric.TOT_BLOOD_LOSS.value] = tot_blood
            morbidity_dict[Metric.TOT_LUNG_LOSS.value] = lung_loss
            morbidity_dict[Metric.HIGHEST_P_BLEEDOUT.value] = calc_prob_bleedout(deathly_person)
            morbidity_dict[Metric.HIGHEST_P_ASPHYXIA.value] = calc_prob_asphyx(deathly_person)
            morbidity_dict[Metric.HIGHEST_BLOOD_LOSS.value] = sum(inj.blood_lost_ml for inj in deathly_person.injuries)
            morbidity_dict[Metric.HIGHEST_LUNG_LOSS.value] = sum(inj.breathing_hp_lost for inj in deathly_person.injuries)
        return morbidity_dict


class MedsimAction(MCAction):
    def __init__(self, action: Actions, casualty_id: str | None = None, supply: str | None = None,
                 location: str | None = None, tag: str | None = None):
        super().__init__()
        self.action: Actions = action
        self.casualty_id: str | None = casualty_id
        self.supply: str | None = supply
        self.location: str | None = location
        self.tag: str | None = tag

    def __str__(self):
        return "%s %s %s %s %s" % (self.action, self.casualty_id, self.supply, self.location, self.tag)

    def get_action_target(self) -> None | str:
        return self.casualty_id

    def lookup(self, attribute: str) -> str | None:
        if attribute == 'casualty_id':
            return self.casualty_id
        if attribute == 'supply':
            return self.supply
        if attribute == 'location':
            return self.location
        if attribute == 'tag':
            return self.tag