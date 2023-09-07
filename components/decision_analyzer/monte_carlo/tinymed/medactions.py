from .tinymed_state import TinymedAction
from .tinymed_enums import Casualty, Supplies, Actions, Locations


def get_treatment_actions(casualties: list[Casualty], supplies: list[str]):
    treatments: list[tuple] = []
    locations: list[str] = [loc.value for loc in Locations]
    for c in casualties:
        casualty_id: str = c.id
        for supply_str in supplies:
            for loc in locations:
                action_tuple: tuple[str, str, str, str] = (Actions.APPLY_TREATMENT.value, casualty_id, supply_str, loc)
                treatments.append(action_tuple)
    return treatments


def get_possible_actions(casualties: list[Casualty], supplies: list[str]) -> list[tuple]:
    possible_action_tuples: list[tuple] = []
    treatment_actions = get_treatment_actions(casualties, supplies)
    # more get_blah_actions_here later

    possible_action_tuples.extend(treatment_actions)
    return possible_action_tuples


def supply_dict_to_list(supplies: dict[Supplies, int]) -> list[str]:
    keylist = list(supplies.keys())
    return list(set(keylist))   # Set removes non  uniques


def create_tm_actions(actions: list[tuple]) -> list[TinymedAction]:
    tm_actions = []
    for act_tuple in actions:
        action = act_tuple[0]
        if action == Actions.APPLY_TREATMENT.value:
            casualty, supply, loc = act_tuple[1:]
            tm_action = TinymedAction(action, casualty_id=casualty, supply=supply, location=loc)
        elif action in [Actions.CHECK_PULSE.value, Actions.CHECK_RESPIRATION.value, Actions.CHECK_ALL_VITALS.value,
                        Actions.MOVE_TO_EVAC.value, Actions.SITREP.value]:
            casualty = act_tuple[1]
            tm_action = TinymedAction(action, casualty_id=casualty)
        elif action == Actions.DIRECT_MOBILE_CASUALTY.value:
            tm_action = TinymedAction(action=action)
        elif action == Actions.TAG_CASUALTY.value:
            casualty, tag = act_tuple[1:]
            tm_action = TinymedAction(action=action, casualty_id=casualty, tag=tag)
        else:
            tm_action = TinymedAction(action=Actions.UNKNOWN)
        tm_actions.append(tm_action)
    return tm_actions


