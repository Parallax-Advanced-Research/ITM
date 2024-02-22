from domain.ta3 import TA3State, Casualty, TagCategory
from domain.internal import Decision, Action, Scenario, TADProbe
from components import Elaborator
from components.decision_analyzer.monte_carlo.medsim.util.medsim_actions import supply_injury_match, supply_location_match
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Actions
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimAction


class TA3Elaborator(Elaborator):

    def elaborate(self, scenario: Scenario, probe: TADProbe) -> list[Decision[Action]]:
        d: Decision[Action]
        to_return: list[Decision[Action]] = []
        for d in probe.decisions:
            if d.id_ == "search":
                continue
            _name = d.value.name
            d.value.params = {k: v for k, v in d.value.params.items() if v is not None}
            if _name == 'APPLY_TREATMENT':
                to_return += self._treatment(probe.state, d)
            elif _name == 'SITREP' or _name == 'DIRECT_MOBILE_CASUALTY' or _name == 'SEARCH': 
                 # These need no param options
                to_return += [d]
            elif _name == 'TAG_CHARACTER':
                to_return += self._tag(probe.state.casualties, d)
            elif _name == 'END_SCENARIO' or _name == 'END_SCENE':
                to_return += [d]
            elif _name == 'MOVE_TO_EVAC':
                to_return += self._add_evac_options(probe, d)
            else:
                to_return += self._ground_casualty(probe.state.casualties, d, injured_only = False)

        final_list = []
        for tr in to_return:
            if tr.value.name == 'DIRECT_MOBILE_CHARACTERS' and 'casualty' in tr.value.params:
                pass
            else:
                final_list.append(tr)
        tag_actions = [d for d in final_list if d.value.name == "TAG_CHARACTER"]
        if len(tag_actions) > 0:
            final_list = tag_actions
        final_list.sort(key=str)
        probe.decisions = final_list
        # Needs direct mobile casualties no
        return final_list

    def _add_evac_options(self, probe: TADProbe, decision: Decision[Action]) -> list[Decision[Action]]:
        if probe.environment['decision_environment']['aid_delay'] == None:
            return []
        actions = self._ground_casualty(probe.state.casualties, decision, injured_only = False)
        breakpoint()

    def _treatment(self, state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        # Ground the decision for all casualties with injuries
        cas_grounded = self._ground_treatments(state, decision)
        return cas_grounded
        #For the metrics evaluation, these checks aren't working or necessary
        
        cas_possible_treatments : list[Decision[Action]] = []
        
        for decision in cas_grounded:
            if decision.value.params.get('location', 'unspecified') == 'internal':
                cas_possible_treatments.append(decision)
                break
            cas_id = decision.value.params['casualty']
            cas = [c for c in state.casualties if c.id == cas_id][0]
            for injury in cas.injuries:
                if decision.value.params.get('location', 'unspecified') in [injury.location, 'unspecified'] \
                   and self.medsim_allows_action(decision.value, injury.name):
                    cas_possible_treatments.append(decision)
                    break
            
        return cas_possible_treatments
        

    def _tag(self, casualties: list[Casualty], decision: Decision[Action]) -> list[Decision[Action]]:
        action = decision.value
        cas_grounded: list[Decision[Action]] = []
        if 'casualty' not in action.params:
            for cas in casualties:
                if not cas.tag and cas.assessed:
                    # Copy the casualty into the params dict
                    cas_params = action.params.copy()
                    cas_params['casualty'] = cas.id
                    cas_grounded.append(Decision(decision.id_, Action(action.name, cas_params), 
                                                 kdmas=decision.kdmas))
        else:
            cas = [c for c in casualties if c.id == action.params['casualty']][0]
            if not cas.tag:
                cas_grounded.append(decision)
        tag_grounded: list[Decision[Action]] = []
        for cas_action in cas_grounded:
            # If no category set, enumerate the tag types
            if 'category' not in cas_action.value.params:
                for tag in TagCategory:
                    tag_params = cas_action.value.params.copy()
                    tag_params['category'] = tag
                    tag_grounded.append(Decision(cas_action.id_, Action(action.name, tag_params), 
                                                 kdmas=cas_action.kdmas))
            else:
                tag_grounded.append(cas_action)
        return tag_grounded

    @staticmethod
    def _ground_treatments(state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        actions = TA3Elaborator._ground_casualty(state.casualties, decision)
        # Ground the decision for all treatments
        treat_grounded: list[Decision[Action]] = []
        for cas_action in actions:
            # If no treatment set, enumerate the supplies
            if 'treatment' not in cas_action.value.params:
                for supply in state.supplies:
                    sup_params = cas_action.value.params.copy()
                    if supply.quantity > 0:
                        sup_params['treatment'] = supply.type
                        treat_grounded.append(Decision(cas_action.id_, Action(decision.value.name, sup_params), kdmas=cas_action.kdmas))
            else:
                supply_needed = cas_action.value.params.copy()['treatment']
                for s in state.supplies:
                    if s.type == supply_needed and s.quantity > 0:
                        treat_grounded.append(cas_action)
                        break

        # Ground the location
        grounded: list[Decision[Action]] = []
        for treat_action in treat_grounded:
            # If no location set, enumerate the injured locations
            if 'location' not in treat_action.value.params:
                if treat_action.value.params['treatment'].lower() == 'nasopharyngeal airway':
                    treat_action.value.params['location'] = 'left face'
                    grounded.append(treat_action)
                    continue
                cas_id = treat_action.value.params['casualty']
                cas = [c for c in state.casualties if c.id == cas_id][0]
                if cas.assessed and not cas.tag:
                    continue
                for injury in cas.injuries:
                    treat_params = treat_action.value.params.copy()
                    if TA3Elaborator.medsim_allows_action(treat_action.value, injury.name):
                        treat_params['location'] = treat_params.get('location', 'unspecified')
                    else:
                        treat_params['location'] = injury.location
                    grounded.append(Decision(treat_action.id_, Action(decision.value.name, treat_params), kdmas=treat_action.kdmas))
            else:
                grounded.append(treat_action)

        return grounded

    @staticmethod
    def _ground_casualty(casualties: list[Casualty], decision: Decision[Action], injured_only = True) -> list[Decision[Action]]:
        action = decision.value
        cas_grounded: list[Decision[Action]] = []
        if 'casualty' not in action.params:
            for cas in casualties:
                if cas.injuries or not injured_only:
                    # Copy the casualty into the params dict
                    cas_params = action.params.copy()
                    cas_params['casualty'] = cas.id
                    cas_grounded.append(Decision(decision.id_, Action(action.name, cas_params), kdmas=decision.kdmas))
        else:
            cas_grounded.append(decision)

        return cas_grounded

    @staticmethod
    def medsim_allows_action(action: Action, injury: str):
        return True
        if not supply_injury_match(action.params['treatment'], injury):
            if action.params['treatment'].lower() == "nasopharyngeal airway" and injury.lower() == "burn":
                pass
            else:
                return False
        if action.params.get('location', 'unspecified') == 'internal':
            return True
        medact = MedsimAction(
                    Actions.APPLY_TREATMENT, 
                    action.params['casualty'], 
                    action.params['treatment'], 
                    action.params.get('location', 'unspecified'), 
                    None)
        if not supply_location_match(medact): 
            return False
        return True
     
