from domain.ta3 import TA3State, Casualty, TagCategory, Supply
from domain.internal import Decision, Action, Scenario, TADProbe
from components import Elaborator
from components.decision_analyzer.monte_carlo.medsim.util.medsim_actions import supply_injury_match, supply_location_match
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Actions
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimAction
from typing import Any

from domain.enum import ActionTypeEnum, SupplyTypeEnum, InjuryTypeEnum, InjuryLocationEnum, \
                        InjuryStatusEnum, ParamEnum, MentalStatusEnum, BreathingLevelEnum, \
                        AvpuLevelEnum


SPECIAL_SUPPLIES = [SupplyTypeEnum.IV_BAG, SupplyTypeEnum.BLOOD, SupplyTypeEnum.PAIN_MEDICATIONS]

class TA3Elaborator(Elaborator):

    def elaborate(self, scenario: Scenario, probe: TADProbe) -> list[Decision[Action]]:
        d: Decision[Action]
        to_return: list[Decision[Action]] = []
        tag_available = len([1 for dtemp in probe.decisions if dtemp.value.name == ActionTypeEnum.TAG_CHARACTER]) > 0
        suggested_treats = \
            [dtemp for dtemp in probe.decisions 
                 if dtemp.value.name == ActionTypeEnum.APPLY_TREATMENT
                     and dtemp.value.params.get(ParamEnum.TREATMENT, None) is not None]
        suggested_checks = \
            [dtemp for dtemp in probe.decisions 
                 if dtemp.value.name == ActionTypeEnum.CHECK_ALL_VITALS]
        for d in probe.decisions:
            if d.id_ == "search":
                continue
            _name = d.value.name
            d.value.params = {k: v for k, v in d.value.params.items() if v is not None}
            if _name == ActionTypeEnum.APPLY_TREATMENT:
                to_return += self._treatment(probe.state, d, tag_available=tag_available)
            elif _name == ActionTypeEnum.SITREP:
                to_return += self._enumerate_sitrep_actions(probe.state, d)
            elif _name == ActionTypeEnum.DIRECT_MOBILE_CHARACTERS: 
                to_return += self._enumerate_direct_actions(probe.state, d)
            elif _name == ActionTypeEnum.CHECK_ALL_VITALS: 
                to_return += self._enumerate_check_actions(probe.state, d)
            elif _name == ActionTypeEnum.CHECK_PULSE:
                to_return += self._enumerate_check_pulse_actions(probe.state, d)
            elif _name == ActionTypeEnum.CHECK_RESPIRATION:
                to_return += self._enumerate_check_resp_actions(probe.state, d)
            elif _name == ActionTypeEnum.SEARCH: 
                pass #No good theory of the search action.
                # to_return += [d]
            elif _name == ActionTypeEnum.TAG_CHARACTER:
                to_return += self._tag(probe.state.casualties, d)
            elif _name == ActionTypeEnum.END_SCENE:
                to_return += [d]
            elif _name == ActionTypeEnum.MOVE_TO_EVAC:
                to_return += self._add_evac_options(probe, d)
            else:
                to_return += self._ground_casualty(probe.state.casualties, d, injured_only = False)

        final_treat_count = \
            len([1 for dtemp in to_return 
                 if dtemp.value.name == ActionTypeEnum.APPLY_TREATMENT])

        #Kluge to bypass Soartech errors. In Soartech scenarios, some apply_treatments are suggested
        #that only make sense with vitals, which are not available. This workaround gets the vitals
        if len(suggested_treats) > 0 and final_treat_count == 0 and len(suggested_checks) == 0:
            to_return += self._enumerate_check_actions(probe.state, Decision("TAD", Action(ActionTypeEnum.CHECK_ALL_VITALS, {})))

        final_list = []
        for tr in to_return:
            if tr.value.name == ActionTypeEnum.DIRECT_MOBILE_CHARACTERS and ParamEnum.CASUALTY in tr.value.params:
                pass
            else:
                final_list.append(tr)
        tag_actions = [d for d in final_list if d.value.name == ActionTypeEnum.TAG_CHARACTER]
        if len(tag_actions) > 0:
            final_list = tag_actions
        final_list.sort(key=str)
        if len(final_list) == 0:
            breakpoint()
        probe.decisions = final_list
        return final_list

    def _add_evac_options(self, probe: TADProbe, decision: Decision[Action]) -> list[Decision[Action]]:
        if probe.environment['decision_environment']['aid_delay'] == None:
            return []
        decisions = self._ground_casualty(probe.state.casualties, decision)
        ret_decisions = []
        for dec in decisions:
            if ParamEnum.EVAC_ID in dec.value.params:
                ret_decisions.append(dec)
            else:
                for aid in probe.environment['decision_environment']['aid_delay']:
                    ret_decisions.append(
                        decision_copy_with_params(decision, {ParamEnum.EVAC_ID: aid['id']}))
        return ret_decisions

    def _enumerate_check_actions(self, state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        # Ground the decision for all casualties with injuries
        dec_grounded = self._ground_casualty(state.casualties, decision, injured_only = False)
        dec_applicable = []

        for cur_decision in dec_grounded:
            cas = get_casualty_by_id(cur_decision.value.params[ParamEnum.CASUALTY], state.casualties)
            if cas.vitals.ambulatory is None:
                dec_applicable.append(cur_decision)
                continue
            if cas.vitals.avpu is None:
                dec_applicable.append(cur_decision)
                continue
            if cas.vitals.breathing is None:
                dec_applicable.append(cur_decision)
                continue
            if cas.vitals.conscious is None:
                dec_applicable.append(cur_decision)
                continue
            if cas.vitals.hrpmin is None:
                dec_applicable.append(cur_decision)
                continue
            # if cas.vitals.spo2 is None:
                # dec_applicable.append(cur_decision)
                # continue
            if not cas.assessed:
                dec_applicable.append(cur_decision)
                
        return dec_applicable

    def _enumerate_check_pulse_actions(self, state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        # Ground the decision for all casualties with injuries
        dec_grounded = self._ground_casualty(state.casualties, decision, injured_only = False)
        dec_applicable = []

        for cur_decision in dec_grounded:
            cas = get_casualty_by_id(cur_decision.value.params[ParamEnum.CASUALTY], state.casualties)
            if cas.vitals.hrpmin is None:
                dec_applicable.append(cur_decision)
                continue
                
        return dec_applicable

    def _enumerate_check_resp_actions(self, state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        # Ground the decision for all casualties with injuries
        dec_grounded = self._ground_casualty(state.casualties, decision, injured_only = False)
        dec_applicable = []

        for cur_decision in dec_grounded:
            cas = get_casualty_by_id(cur_decision.value.params[ParamEnum.CASUALTY], state.casualties)
            if cas.vitals.breathing is None:
                dec_applicable.append(cur_decision)
                continue
                
        return dec_applicable

    def _enumerate_sitrep_actions(self, state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        # Ground the decision for all casualties with injuries
        dec_grounded = self._ground_casualty(state.casualties, decision, injured_only = False)
        dec_applicable = []
        
        for cur_decision in dec_grounded:
            cas = get_casualty_by_id(cur_decision.value.params[ParamEnum.CASUALTY], state.casualties)
            if cas.vitals.mental_status not in [None, MentalStatusEnum.CALM, MentalStatusEnum.AGONY, MentalStatusEnum.UPSET]:
                continue
            if cas.vitals.ambulatory is None:
                dec_applicable.append(cur_decision)
                continue
            if cas.vitals.avpu is None:
                dec_applicable.append(cur_decision)
                continue
            if cas.vitals.breathing is None:
                dec_applicable.append(cur_decision)
                continue
            if cas.vitals.conscious is None:
                dec_applicable.append(cur_decision)
                continue
            if not cas.assessed:
                dec_applicable.append(cur_decision)
                continue
                
        if len(dec_applicable) > 1 and ParamEnum.CASUALTY not in decision.value.params:
            dec_applicable.append(decision)
            
        return dec_applicable


    def _enumerate_direct_actions(self, state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        return []

    def _treatment(self, state: TA3State, decision: Decision[Action], tag_available = True) -> list[Decision[Action]]:
        # If it's already fully grounded, don't second-guess the server
        if (ParamEnum.TREATMENT in decision.value.params 
              and ParamEnum.CASUALTY in decision.value.params
              and ParamEnum.LOCATION in decision.value.params):
            return [decision]
            
        # If it's already mostly grounded, don't second-guess the server
        if (ParamEnum.TREATMENT in decision.value.params 
              and ParamEnum.CASUALTY in decision.value.params
              and decision.value.params[ParamEnum.TREATMENT] in SPECIAL_SUPPLIES):
            decision.value.params[ParamEnum.LOCATION] = InjuryLocationEnum.UNSPECIFIED
            return [decision]

        # Ground the decision for all casualties with injuries
        dec_grounded = self._ground_treatments(state, decision, tag_available=tag_available)
        
        dec_possible_treatments : list[Decision[Action]] = []
        
        for d in dec_grounded:
            cas = get_casualty_by_id(d.value.params[ParamEnum.CASUALTY], state.casualties)
            for injury in cas.injuries:
                if d.value.params.get(ParamEnum.TREATMENT) == SupplyTypeEnum.DECOMPRESSION_NEEDLE\
                       and "chest" in d.value.params.get(ParamEnum.LOCATION) \
                       and injury.location == d.value.params.get(ParamEnum.LOCATION) \
                       and injury.name == InjuryTypeEnum.BROKEN_BONE \
                       and injury.status == InjuryStatusEnum.VISIBLE:
                    dec_possible_treatments.append(d)
                    break
                if injury.location != d.value.params[ParamEnum.LOCATION]:
                    continue
                if self.medsim_allows_action(d.value, injury.name):
                    dec_possible_treatments.append(d)
                    break
                    
            if d.value.params.get(ParamEnum.TREATMENT) == SupplyTypeEnum.VENTED_CHEST_SEAL \
                    and d.value.params.get(ParamEnum.LOCATION) == InjuryLocationEnum.UNSPECIFIED:
                d.value.params[ParamEnum.LOCATION] = InjuryLocationEnum.LEFT_CHEST
            
        for cas in state.casualties:
            if decision.value.params.get(ParamEnum.CASUALTY, None) not in [None, cas.id]:
                continue
            new_treatments = []
            if ((cas.vitals.breathing in [BreathingLevelEnum.RESTRICTED, BreathingLevelEnum.NONE] 
                    or InjuryTypeEnum.BURN in [injury.name for injury in cas.injuries])
                 and decision.value.params.get(ParamEnum.TREATMENT, SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY)
                      == SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY
                 and self._supply_quantity(state, SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY) > 0):
                if (decision.value.params.get(ParamEnum.LOCATION, InjuryLocationEnum.LEFT_FACE)
                       == InjuryLocationEnum.LEFT_FACE):
                    new_treatments.append(
                        decision_copy_with_params(decision, 
                            {ParamEnum.CASUALTY: cas.id,
                             ParamEnum.LOCATION: InjuryLocationEnum.LEFT_FACE,
                             ParamEnum.TREATMENT: SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY}))
                elif (decision.value.params.get(ParamEnum.LOCATION, InjuryLocationEnum.RIGHT_FACE)
                        == InjuryLocationEnum.RIGHT_FACE):
                    new_treatments.append(
                        decision_copy_with_params(decision, 
                            {ParamEnum.CASUALTY: cas.id,
                             ParamEnum.LOCATION: InjuryLocationEnum.RIGHT_FACE,
                             ParamEnum.TREATMENT: SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY}))
            if ((cas.vitals.mental_status == MentalStatusEnum.AGONY 
                    or cas.vitals.avpu == AvpuLevelEnum.PAIN
                    or len(cas.injuries) > 0)
#                )
                 and decision.value.params.get(ParamEnum.TREATMENT, SupplyTypeEnum.PAIN_MEDICATIONS) == SupplyTypeEnum.PAIN_MEDICATIONS
                 and self._supply_quantity(state, SupplyTypeEnum.PAIN_MEDICATIONS) > 0):
                new_treatments.append(
                    decision_copy_with_params(decision, 
                        {ParamEnum.CASUALTY: cas.id,
                         ParamEnum.LOCATION: InjuryLocationEnum.UNSPECIFIED,
                         ParamEnum.TREATMENT: SupplyTypeEnum.PAIN_MEDICATIONS}))
            dec_possible_treatments += new_treatments
            # dec_possible_treatments += \
                # [t for t in new_treatments if t.value.params[ParamEnum.TREATMENT] not in cas.treatments]
        return list({consistent_decision_key(d):d for d in dec_possible_treatments}.values())
        


    def _tag(self, casualties: list[Casualty], decision: Decision[Action]) -> list[Decision[Action]]:
        action = decision.value
        dec_grounded: list[Decision[Action]] = []
        if ParamEnum.CASUALTY not in action.params:
            for cas in casualties:
                if not cas.tag and cas.assessed:
                    # Copy the casualty into the params dict
                    cas_params = action.params.copy()
                    cas_params[ParamEnum.CASUALTY] = cas.id
                    dec_grounded.append(Decision(decision.id_, Action(action.name, cas_params), 
                                                 kdmas=decision.kdmas))
        else:
            cas = get_casualty_by_id(action.params[ParamEnum.CASUALTY], casualties)
            if not cas.tag:
                dec_grounded.append(decision)
        tag_grounded: list[Decision[Action]] = []
        for cas_action in dec_grounded:
            # If no category set, enumerate the tag types
            if ParamEnum.CATEGORY not in cas_action.value.params:
                for tag in TagCategory:
                    tag_params = cas_action.value.params.copy()
                    tag_params[ParamEnum.CATEGORY] = tag
                    tag_grounded.append(Decision(cas_action.id_, Action(action.name, tag_params), 
                                                 kdmas=cas_action.kdmas))
            else:
                tag_grounded.append(cas_action)
        return tag_grounded

    def _supply_quantity(self, state: TA3State, supply_type: str):
        for supply in state.supplies:
            if supply.type == supply_type:
                return supply.quantity
        return 0

    @staticmethod
    def _ground_treatments(state: TA3State, decision: Decision[Action], tag_available: bool = True) -> list[Decision[Action]]:
        actions = TA3Elaborator._ground_casualty(state.casualties, decision)
        # Ground the decision for all treatments
        treat_grounded: list[Decision[Action]] = []
        for cas_action in actions:
            # If no treatment set, enumerate the supplies
            if ParamEnum.TREATMENT not in cas_action.value.params:
                for supply in supply_filter(state.supplies):
                    sup_params = cas_action.value.params.copy()
                    if supply.quantity > 0:
                        sup_params[ParamEnum.TREATMENT] = supply.type
                        treat_grounded.append(Decision(cas_action.id_, Action(decision.value.name, sup_params), kdmas=cas_action.kdmas))
            else:
                supply_needed = cas_action.value.params.copy()[ParamEnum.TREATMENT]
                for s in state.supplies:
                    if s.type == supply_needed and s.quantity > 0:
                        treat_grounded.append(cas_action)
                        break

        # Ground the location
        grounded: list[Decision[Action]] = []
        for treat_action in treat_grounded:
            # If no location set, enumerate the injured locations
            if ParamEnum.LOCATION not in treat_action.value.params:
                cas = get_casualty_by_id(treat_action.value.params[ParamEnum.CASUALTY], state.casualties)
                if tag_available and cas.assessed and not cas.tag:
                    continue
                if cas.vitals.breathing in [BreathingLevelEnum.RESTRICTED, BreathingLevelEnum.NONE] \
                   and treat_action.value.params[ParamEnum.TREATMENT] == SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY:
                    treat_action.value.params[ParamEnum.LOCATION] = InjuryLocationEnum.LEFT_FACE
                    grounded.append(treat_action)
                    continue
                for injury in cas.injuries:
                    if injury.status == 'treated':
                        continue
                    treat_params = treat_action.value.params.copy()
                    if TA3Elaborator.medsim_allows_action(treat_action.value, injury.name):
                        treat_params[ParamEnum.LOCATION] = treat_params.get(ParamEnum.LOCATION, InjuryLocationEnum.UNSPECIFIED)
                    else:
                        treat_params[ParamEnum.LOCATION] = injury.location
                    grounded.append(Decision(treat_action.id_, Action(decision.value.name, treat_params), kdmas=treat_action.kdmas))
            else:
                grounded.append(treat_action)

        return grounded
        
        
    
        

    @staticmethod
    def _ground_casualty(casualties: list[Casualty], decision: Decision[Action], injured_only = True) -> list[Decision[Action]]:
        action = decision.value
        dec_grounded: list[Decision[Action]] = []
        if ParamEnum.CASUALTY not in action.params:
            for cas in casualties:
                if cas.injuries or not injured_only:
                    # Copy the casualty into the params dict
                    cas_params = action.params.copy()
                    cas_params[ParamEnum.CASUALTY] = cas.id
                    dec_grounded.append(Decision(decision.id_, Action(action.name, cas_params), kdmas=decision.kdmas))
        else:
            dec_grounded.append(decision)

        return dec_grounded

    @staticmethod
    def medsim_allows_action(action: Action, injury: str):
        if not supply_injury_match(action.params[ParamEnum.TREATMENT], injury):
            if action.params[ParamEnum.TREATMENT] == SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY \
               and injury == InjuryTypeEnum.BURN:
                pass
            else:
                return False
        # if action.params.get(ParamEnum.LOCATION, InjuryLocationEnum.UNSPECIFIED) == InjuryLocationEnum.INTERNAL:
            # return True
        medact = MedsimAction(
                    Actions.APPLY_TREATMENT, 
                    action.params[ParamEnum.CASUALTY], 
                    action.params[ParamEnum.TREATMENT], 
                    action.params.get(ParamEnum.LOCATION, InjuryLocationEnum.UNSPECIFIED), 
                    None)
        if not supply_location_match(medact): 
            return False
        return True
        
def consistent_decision_key(dec : Decision) -> str:
    return (dec.value.name + "(" + dec.value.params.get(ParamEnum.CASUALTY, "") + ","
                                 + dec.value.params.get(ParamEnum.TREATMENT, "") + ","
                                 + dec.value.params.get(ParamEnum.LOCATION, "") + ","
                                 + dec.value.params.get(ParamEnum.CATEGORY, "") + ")")

def get_casualty_by_id(id: str, casualties: list[Casualty]) -> Casualty:
    return [c for c in casualties if c.id == id][0]

def decision_copy_with_params(dec: Decision[Action], params: dict[str, Any]):
    pcopy = dec.value.params.copy() | params
    return Decision(dec.id_, Action(dec.value.name, pcopy), kdmas=dec.kdmas)

def supply_filter(supplies: list[Supply]):
    return [s for s in supplies if s.type not in SPECIAL_SUPPLIES]
        
