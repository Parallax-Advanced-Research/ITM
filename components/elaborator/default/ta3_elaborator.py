import json

from domain.ta3 import TA3State, Casualty, TagCategory, Supply
from domain.internal import Decision, Action, Scenario, TADProbe, make_new_action_decision, update_decision_parameters
from components import Elaborator
from components.decision_analyzer.monte_carlo.medsim.util.medsim_actions import supply_injury_match, supply_location_match
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Actions
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimAction
from typing import Any
import os

from domain.enum import ActionTypeEnum, SupplyTypeEnum, InjuryTypeEnum, InjuryLocationEnum, \
                        InjuryStatusEnum, ParamEnum, MentalStatusEnum, BreathingLevelEnum, \
                        AvpuLevelEnum


SPECIAL_SUPPLIES = [SupplyTypeEnum.BLANKET, SupplyTypeEnum.BLOOD, SupplyTypeEnum.EPI_PEN, \
                    SupplyTypeEnum.FENTANYL_LOLLIPOP, SupplyTypeEnum.IV_BAG, \
                    SupplyTypeEnum.PAIN_MEDICATIONS, SupplyTypeEnum.PULSE_OXIMETER]

ID_LABELS = ["id", "type", "threat_type", "location"]

class TA3Elaborator(Elaborator):

    def __init__(self, elab_to_json: bool):
        self.elab_to_json = elab_to_json

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
            elif _name == ActionTypeEnum.CHECK_BLOOD_OXYGEN:
                to_return += self._enumerate_check_blood_oxygen_actions(probe.state, d)
            elif _name == ActionTypeEnum.CHECK_RESPIRATION:
                to_return += self._enumerate_check_resp_actions(probe.state, d)
            elif _name == ActionTypeEnum.SEARCH: 
                # This one doesn't need elaboration, I think?
                to_return += [d]
            elif _name == ActionTypeEnum.TAG_CHARACTER:
                to_return += self._tag(probe.state.casualties, d)
            elif _name == ActionTypeEnum.END_SCENE:
                to_return += [d]
            elif _name == ActionTypeEnum.MOVE_TO:
                to_return += self._add_move_options(probe, d)
            elif _name == ActionTypeEnum.MOVE_TO_EVAC:
                to_return += self._add_evac_options(probe, d)
            elif _name == ActionTypeEnum.MESSAGE:
                to_return += self._add_message_options(probe, d)
            else:
                to_return += self._ground_casualty(probe.state.casualties, d, injured_only = False)

        final_treat_count = \
            len([1 for dtemp in to_return 
                 if dtemp.value.name == ActionTypeEnum.APPLY_TREATMENT])

        #Kluge to bypass Soartech errors. In Soartech scenarios, some apply_treatments are suggested
        #that only make sense with vitals, which are not available. This workaround gets the vitals
        # if len(suggested_treats) > 0 and final_treat_count == 0 and len(suggested_checks) == 0:
            # breakpoint()
            # to_return += self._enumerate_check_actions(
                            # probe.state, 
                            # make_new_action_decision("TAD", ActionTypeEnum.CHECK_ALL_VITALS, {}, None, False))
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
        # final_list = remove_too_frequent_actions(probe, final_list)
        probe.decisions = final_list
        if self.elab_to_json:
            self._export_elab_to_json(final_list, scenario.id_)
        return final_list

    def _export_elab_to_json(self, final_list, scen_name):
        file_name = os.path.join('data', 'elab_output', f'{scen_name}.json')
        if os.path.exists(file_name):
            # doing this check as elaborator is called many times per scene, this way the first time ran is the only
            #  one saved
            return
        action_dict = []
        for decision in final_list:
            action = decision.value.name
            casualty = decision.value.params.get('casualty', None)
            location = decision.value.params.get('location', None)
            supply = decision.value.params.get('treatment', None)
            act_json = {'action': action, 'casualty': casualty, 'treatment': supply, 'location': location}
            action_dict.append(act_json)

        total_dict = {'Actions': action_dict}

        with open(file_name, 'w') as out:
            json.dump(total_dict, out)

    def _add_evac_options(self, probe: TADProbe, decision: Decision[Action]) -> list[Decision[Action]]:
        if probe.environment['decision_environment']['aid'] == None:
            return []
        decisions = self._ground_casualty(probe.state.casualties, decision, unseen = None)
        ret_decisions = []
        for dec in decisions:
            if ParamEnum.EVAC_ID in dec.value.params:
                ret_decisions.append(dec)
            else:
                for aid in probe.environment['decision_environment']['aid']:
                    ret_decisions.append(
                        decision_copy_with_params(decision, {ParamEnum.EVAC_ID: aid['id']}))
        return ret_decisions

    def _add_message_options(self, probe: TADProbe, decision: Decision[Action]) -> list[Decision[Action]]:
        if decision.value.params["type"] != "justify":
            decision.context.update(decision.value.params)
            return [decision]
        if len(probe.state.actions_performed) == 0:
            return []
        for state_referent in [s.strip(" ")[1:-1] for s in decision.value.params["relevant_state"].split(",")]:
            topic = self.get_topic(state_referent)
            newCount = decision.context.get("topic_" + topic, 0) + 1
            decision.context["topic_" + topic] = newCount
            decision.context["val_" + topic + str(newCount)] = \
                self.dereference(state_referent, probe.state.orig_state)
        decision.context["last_action"] = probe.state.actions_performed[-1].name
        for (k, v) in probe.state.actions_performed[-1].params.items():
            decision.context["last_" + k] = v
        decision.context["action_type"] = "justify"
        return [decision]

    def get_topic(self, referent: str):
        if "." in referent:
            return referent[referent.rindex(".") + 1:]
        else:
            return referent
    
    def dereference(self, referent: str, data: dict[str, Any]):
        assert(len(referent) > 0)
        assert(type(data) is dict)
        key = referent
        rest = None
        if "." in referent:
            dotIndex = referent.index(".")
            assert(dotIndex > 0)
            key = referent[0:dotIndex]
            rest = referent[dotIndex+1:]

        valIndex = None
        if "[" in key:
            assert(key.endswith("]"))
            bracketIndex = key.index("[")
            valIndex = key[bracketIndex+1:-1]
            key = key[0:bracketIndex]
        
        assert(key in data)
        obj = data[key]
        
        if valIndex is not None:
            assert(type(obj) is list)
            foundObj = None
            for item in obj:
                if self.getID(item) == valIndex:
                    foundObj = item
                    break
            if foundObj is None:
                raise Exception("No item corresponding to identifier " + valIndex)
            else:
                obj = foundObj

        if rest is None:
            if type(obj) is list:
                return str(obj)
            else:
                return obj
        else:
            return self.dereference(rest, obj)
            
                    
    def getID(self, item: dict[str, Any]):
        assert(type(item) is dict)
        for label in ID_LABELS:
            if label in item:
                return item[label]
        raise Exception("Attempting to dereference index of object with no ID.")


    def _add_move_options(self, probe: TADProbe, decision: Decision[Action]) -> list[Decision[Action]]:
        decisions = self._ground_casualty(probe.state.casualties, decision, unseen=True)
        return decisions

    def _enumerate_check_actions(self, state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        # Ground the decision for all casualties with injuries
        dec_grounded = self._ground_casualty(state.casualties, decision, injured_only = False)
        dec_applicable = []

        for cur_decision in dec_grounded:
            cas = get_casualty_by_id(cur_decision.value.params[ParamEnum.CASUALTY], state.casualties)
            # if cas.vitals.ambulatory is None:
                # dec_applicable.append(cur_decision)
                # continue
            # if cas.vitals.avpu is None:
                # dec_applicable.append(cur_decision)
                # continue
            # if cas.vitals.breathing is None:
                # dec_applicable.append(cur_decision)
                # continue
            # if cas.vitals.conscious is None:
                # dec_applicable.append(cur_decision)
                # continue
            if cas.vitals.hrpmin is None:
                dec_applicable.append(cur_decision)
                continue
            if cas.vitals.spo2 is None and TA3Elaborator._supply_available(state, SupplyTypeEnum.PULSE_OXIMETER):
                dec_applicable.append(cur_decision)
                continue
            if not cas.assessed:
                dec_applicable.append(cur_decision)
                
        return dec_applicable

    def _enumerate_check_blood_oxygen_actions(self, state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        if not TA3Elaborator._supply_available(state, SupplyTypeEnum.PULSE_OXIMETER):
            return []

        # Ground the decision for all casualties
        dec_grounded = self._ground_casualty(state.casualties, decision, injured_only = False)
        dec_applicable = []

        for cur_decision in dec_grounded:
            cas = get_casualty_by_id(cur_decision.value.params[ParamEnum.CASUALTY], state.casualties)
            if not cas.assessed:
                dec_applicable.append(cur_decision)
                continue
            if cas.vitals.spo2 is None:
                dec_applicable.append(cur_decision)
                continue
                
        return dec_applicable

    def _enumerate_check_pulse_actions(self, state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        # Ground the decision for all casualties with injuries
        dec_grounded = self._ground_casualty(state.casualties, decision, injured_only = False)
        dec_applicable = []

        for cur_decision in dec_grounded:
            cas = get_casualty_by_id(cur_decision.value.params[ParamEnum.CASUALTY], state.casualties)
            if not cas.assessed:
                dec_applicable.append(cur_decision)
                continue
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
            if not cas.assessed:
                dec_applicable.append(cur_decision)
                continue
                
        return dec_applicable

    def _enumerate_sitrep_actions(self, state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        # Ground the decision for all casualties with injuries
        dec_grounded = self._ground_casualty(state.casualties, decision, injured_only = False)
        dec_applicable = []
        
        for cur_decision in dec_grounded:
            cas = get_casualty_by_id(cur_decision.value.params[ParamEnum.CASUALTY], state.casualties)
            # if cas.vitals.mental_status not in [None, MentalStatusEnum.CALM, MentalStatusEnum.AGONY, MentalStatusEnum.UPSET]:
                # continue
            # if cas.vitals.ambulatory is None:
                # dec_applicable.append(cur_decision)
                # continue
            # if cas.vitals.avpu is None:
                # dec_applicable.append(cur_decision)
                # continue
            # if cas.vitals.breathing is None:
                # dec_applicable.append(cur_decision)
                # continue
            # if cas.vitals.conscious is None:
                # dec_applicable.append(cur_decision)
                # continue
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
            return decisions_if_supplied(state, [decision])
            
        # If it's already mostly grounded, don't second-guess the server
        if (ParamEnum.TREATMENT in decision.value.params 
              and ParamEnum.CASUALTY in decision.value.params
              and decision.value.params[ParamEnum.TREATMENT] in SPECIAL_SUPPLIES):
            decision.value.params[ParamEnum.LOCATION] = InjuryLocationEnum.UNSPECIFIED
            return decisions_if_supplied(state, [decision])

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
        dec_possible_treatments = decisions_if_supplied(state, dec_possible_treatments)
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
                    dec_grounded.append(update_decision_parameters(decision, cas_params))
        else:
            cas = get_casualty_by_id(action.params[ParamEnum.CASUALTY], casualties)
            if not cas.tag:
                dec_grounded.append(decision)
        tag_grounded: list[Decision[Action]] = []
        for cas_decision in dec_grounded:
            # If no category set, enumerate the tag types
            if ParamEnum.CATEGORY not in cas_decision.value.params:
                for tag in TagCategory:
                    tag_params = cas_decision.value.params.copy()
                    tag_params[ParamEnum.CATEGORY] = tag
                    tag_grounded.append(update_decision_parameters(cas_decision, tag_params)); 
            else:
                tag_grounded.append(cas_decision)
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
        for cas_decision in actions:
            # If no treatment set, enumerate the supplies
            if ParamEnum.TREATMENT not in cas_decision.value.params:
                for supply in supply_filter(state.supplies):
                    sup_params = cas_decision.value.params.copy()
                    if supply.quantity > 0:
                        sup_params[ParamEnum.TREATMENT] = supply.type
                        treat_grounded.append(update_decision_parameters(cas_decision, sup_params))
            else:
                if TA3Elaborator._supply_available(state, cas_decision.value.params[ParamEnum.TREATMENT]):
                    treat_grounded.append(cas_decision)
                    break

        # Ground the location
        grounded: list[Decision[Action]] = []
        for treat_decision in treat_grounded:
            # If no location set, enumerate the injured locations
            if ParamEnum.LOCATION not in treat_decision.value.params:
                cas = get_casualty_by_id(treat_decision.value.params[ParamEnum.CASUALTY], state.casualties)
                if tag_available and cas.assessed and not cas.tag:
                    continue
                if cas.vitals.breathing in [BreathingLevelEnum.RESTRICTED, BreathingLevelEnum.NONE] \
                   and treat_decision.value.params[ParamEnum.TREATMENT] == SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY:
                    treat_decision.value.params[ParamEnum.LOCATION] = InjuryLocationEnum.LEFT_FACE
                    grounded.append(treat_decision)
                    continue
                for injury in cas.injuries:
                    if injury.status == 'treated':
                        continue
                    treat_params = treat_decision.value.params.copy()
                    treat_params[ParamEnum.LOCATION] = injury.location
                    new_treat_action = Action(decision.value.name, treat_params)
                    if TA3Elaborator.medsim_allows_action(new_treat_action, injury.name):
                        grounded.append(update_decision_parameters(treat_decision, new_treat_action.params))
                    elif TA3Elaborator.medsim_allows_action(treat_decision.value, injury.name):
                        treat_params = treat_decision.value.params.copy()
                        treat_params[ParamEnum.LOCATION] = treat_params.get(ParamEnum.LOCATION, InjuryLocationEnum.UNSPECIFIED)
                        grounded.append(update_decision_parameters(treat_decision, treat_params))
            else:
                grounded.append(treat_decision)

        return grounded
        
        
    @staticmethod 
    def _supply_available(state: TA3State, supply: str):
        for s in state.supplies:
            if s.type == supply and s.quantity > 0:
                return True
        return False
        
    
        

    @staticmethod
    def _ground_casualty(casualties: list[Casualty], decision: Decision[Action], injured_only = True, unseen=False) -> list[Decision[Action]]:
        action = decision.value
        dec_grounded: list[Decision[Action]] = []
        if action.params.get(ParamEnum.CASUALTY, None) is None:
            for cas in casualties:
                if unseen is not None and cas.unseen != unseen:
                    continue
                if cas.injuries or not injured_only:
                    # Copy the casualty into the params dict
                    cas_params = action.params.copy()
                    cas_params[ParamEnum.CASUALTY] = cas.id
                    dec_grounded.append(update_decision_parameters(decision, cas_params))
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


def decisions_if_supplied(state: TA3State, decisions: list[Decision]):
    ret = []
    for decision in decisions:
        if TA3Elaborator._supply_available(state, decision.value.params[ParamEnum.TREATMENT]):
            ret.append(decision)
    return ret

        
def consistent_decision_key(dec : Decision) -> str:
    return (dec.value.name + "(" + dec.value.params.get(ParamEnum.CASUALTY, "") + ","
                                 + dec.value.params.get(ParamEnum.TREATMENT, "") + ","
                                 + dec.value.params.get(ParamEnum.LOCATION, "") + ","
                                 + dec.value.params.get(ParamEnum.CATEGORY, "") + ")")

def get_casualty_by_id(id: str, casualties: list[Casualty]) -> Casualty:
    return [c for c in casualties if c.id == id][0]

def decision_copy_with_params(dec: Decision[Action], params: dict[str, Any]):
    pcopy = dec.value.params.copy() | params
    return update_decision_parameters(dec, pcopy)

def supply_filter(supplies: list[Supply]):
    return [s for s in supplies if s.type not in SPECIAL_SUPPLIES]
        
def remove_too_frequent_actions(probe, dec_list):
    action_counts = {}
    for act in probe.state.actions_performed:
        action_counts[str(act)] = action_counts.get(str(act), 0) + 1
    return [d for d in dec_list if action_counts.get(str(d.value), 0) < 5]
