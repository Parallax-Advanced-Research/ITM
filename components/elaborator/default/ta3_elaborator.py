from domain.ta3 import TA3State, Casualty, TagCategory
from domain.internal import Decision, Action, Scenario, Probe
from components import Elaborator


class TA3Elaborator(Elaborator):
    def elaborate(self, scenario: Scenario, probe: Probe) -> list[Decision[Action]]:
        d: Decision[Action]
        to_return: list[Decision[Action]] = []
        for d in probe.decisions:
            _name = d.value.name
            d.value.params = {k: v for k, v in d.value.params.items() if v is not None}
            if _name == 'APPLY_TREATMENT':
                to_return += self._treatment(probe.state, d)
            elif _name == 'SITREP' or _name == 'DIRECT_MOBILE_CASUALTIES':
                to_return += [d]
            elif _name == 'TAG_CASUALTY':
                to_return += self._tag(probe.state.casualties, d)
            elif _name == 'END_SCENARIO':
                to_return += [d]
            else:
                to_return += self._ground_casualty(probe.state.casualties, d, injured_only = False)


        probe.decisions = to_return
        return to_return

    def _treatment(self, state: TA3State, decision: Decision[Action]) -> list[Decision[Action]]:
        action = decision.value

        # Ground the decision for all casualties with injuries
        cas_grounded = self._ground_casualty(state.casualties, decision)

        # Ground the decision for all treatments
        treat_grounded: list[Decision[Action]] = []
        for cas_action in cas_grounded:
            # If no treatment set, enumerate the supplies
            if 'treatment' not in cas_action.value.params:
                for supply in state.supplies:
                    sup_params = cas_action.value.params.copy()
                    if supply.quantity > 0:
                        sup_params['treatment'] = supply.type
                        treat_grounded.append(Decision(cas_action.id_, Action(action.name, sup_params), kdmas=cas_action.kdmas))
            else:
                treat_grounded.append(cas_action)

        # Ground the location
        grounded: list[Decision[Action]] = []
        for treat_action in treat_grounded:
            # If no location set, enumerate the injured locations
            if 'location' not in treat_action.value.params:
                cas_id = treat_action.value.params['casualty']
                cas = [c for c in state.casualties if c.id == cas_id][0]
                for injury in cas.injuries:
                    treat_params = treat_action.value.params.copy()
                    treat_params['location'] = injury.location
                    grounded.append(Decision(treat_action.id_, Action(action.name, treat_params), kdmas=treat_action.kdmas))
            else:
                grounded.append(treat_action)

        return grounded

    def _tag(self, casualties: list[Casualty], decision: Decision[Action]) -> list[Decision[Action]]:
        action = decision.value
        cas_grounded: list[Decision[Action]] = []
        if 'casualty' not in action.params:
            for cas in casualties:
                if not cas.tag:
                    # Copy the casualty into the params dict
                    cas_params = action.params.copy()
                    cas_params['casualty'] = cas.id
                    cas_grounded.append(Decision(decision.id_, Action(action.name, cas_params), kdmas=decision.kdmas))
        tag_grounded: list[Decision[Action]] = []
        for cas_action in cas_grounded:
            # If no category set, enumerate the tag types
            if 'category' not in cas_action.value.params:
                for tag in TagCategory:
                    tag_params = cas_action.value.params.copy()
                    tag_params['category'] = tag
                    tag_grounded.append(Decision(cas_action.id_, Action(action.name, tag_params), kdmas=cas_action.kdmas))
            else:
                tag_grounded.append(cas_action)
        return tag_grounded

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