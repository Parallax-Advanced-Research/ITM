from domain.ta3.ta3_state import (Supply as TA_SUPPLY, Demographics as TA_DEM, Vitals as TA_VIT,
                                  Injury as TA_INJ, Casualty as TA_CAS, TA3State)
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Demographics, Vitals, Injury, Injuries, Casualty, Locations, Supply
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimAction
from components.decision_analyzer.monte_carlo.medsim.smol.smol_oracle import INJURY_UPDATE, INITIAL_SEVERITIES, BodySystemEffect
from domain.external import Action
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimState


def _convert_demographic(ta_demographic: TA_DEM) -> Demographics:
    return Demographics(age=ta_demographic.age, sex=ta_demographic.sex, rank=ta_demographic.rank)


def _reverse_convert_demographic(internal_demographic: Demographics) -> TA_DEM:
    return TA_DEM(age=internal_demographic.age, sex=internal_demographic.sex, rank=internal_demographic.rank)


def _convert_vitals(ta_vitals: TA_VIT) -> Vitals:
    return Vitals(conscious=ta_vitals.conscious, mental_status=ta_vitals.mental_status,
                  breathing=ta_vitals.breathing, hrpmin=ta_vitals.hrpmin)


def _reverse_convert_vitals(internal_vitals: Vitals) -> TA_VIT:
    return TA_VIT(conscious=internal_vitals.conscious, mental_status=internal_vitals.mental_status,
                  breathing=internal_vitals.breathing, hrpmin=internal_vitals.hrpmin)


def _convert_injury(ta_injury: TA_INJ) -> list[Injury]:
    if ta_injury.severity is None:
        severe = INITIAL_SEVERITIES[ta_injury.name] if ta_injury.name in INITIAL_SEVERITIES.keys() else 0.7
    else:
        severe = ta_injury.severity
    injuries = []
    effect = INJURY_UPDATE[ta_injury.name]
    if ta_injury.name == Injuries.BURN.value:
        burn_suffocation_injury = Injury(name=Injuries.BURN_SUFFOCATION.value, location=Locations.LEFT_FACE.value,
                                         severity=ta_injury.severity,
                                         breathing_effect=INJURY_UPDATE[Injuries.BURN_SUFFOCATION.value].breathing_effect,
                                         bleeding_effect=BodySystemEffect.NONE.value,
                                         burning_effect=BodySystemEffect.NONE.value)
        injuries.append(burn_suffocation_injury)
    burn_tissue_injury = Injury(name=ta_injury.name, location=ta_injury.location, severity=severe,
                                burning_effect=effect.burning_effect, bleeding_effect=effect.bleeding_effect,
                                breathing_effect=effect.breathing_effect)
    injuries.append(burn_tissue_injury)
    return injuries


def _reverse_convert_injury(internal_injury: Injury) -> TA_INJ:
    return TA_INJ(location=internal_injury.location, name=internal_injury.name,
                  severity=internal_injury.severity, treated=internal_injury.treated)


def _convert_casualty(ta_casualty: TA_CAS) -> Casualty:
    demos = ta_casualty.demographics
    dem = _convert_demographic(demos)
    injuries = []
    for inj in ta_casualty.injuries:
        injuries.extend(_convert_injury(inj))
    vit = _convert_vitals(ta_casualty.vitals)

    return Casualty(id=ta_casualty.id, unstructured=ta_casualty.unstructured, name=ta_casualty.name,
                    relationship=ta_casualty.relationship, demographics=dem,injuries=injuries,
                    vitals=vit, complete_vitals=vit, assessed=ta_casualty.assessed, tag=ta_casualty.tag)


def _reverse_convert_casualty(internal_casualty: Casualty) -> TA_CAS:
    ta_demos = _reverse_convert_demographic(internal_casualty.demographics)
    ta_injuries = []
    for inj in internal_casualty.injuries:
        ta_injuries.append(_reverse_convert_injury(inj))
    ta_vitals = _reverse_convert_vitals(internal_casualty.vitals)
    return TA_CAS(id=internal_casualty.id, name=internal_casualty.name, injuries=ta_injuries, demographics=ta_demos,
                  vitals=ta_vitals, tag=internal_casualty.tag, assessed=internal_casualty.assessed,
                  unstructured=internal_casualty.unstructured, relationship=internal_casualty.relationship,
                  treatments=list())


def convert_casualties(ta_casualties: list[TA_CAS]) -> list[Casualty]:
    casualties: list[Casualty] = []
    for cas in ta_casualties:
        casualties.append(_convert_casualty(cas))
    return casualties


def reverse_convert_casualties(internal_casualties: list[Casualty]) -> list[TA_CAS]:
    casualties: list[TA_CAS] = []
    for cas in internal_casualties:
        casualties.append(_reverse_convert_casualty(cas))
    return casualties


def convert_supplies(ta_supplies: list[TA_SUPPLY]) -> list[Supply]:
    supplies: list[Supply] = []
    for ta_sup in ta_supplies:
        # TODO: not seeing reusable at this point, not sure how it will come across
        supplies.append(Supply(ta_sup.type, False, ta_sup.quantity))
    return supplies


def reverse_convert_supplies(internal_supplies: list[Supply]) -> list[TA_SUPPLY]:
    supplies: list[TA_SUPPLY] = []
    for supply in list(internal_supplies):
        ta_supply: TA_SUPPLY = TA_SUPPLY(type=supply.name, quantity=supply.amount)  # TODO do something with reusable
        supplies.append(ta_supply)
    return supplies


def convert_state(ta3_state: TA3State) -> MedsimState:
    cas = convert_casualties(ta3_state.casualties)
    sup = convert_supplies(ta3_state.supplies)
    return MedsimState(casualties=cas, supplies=sup, time=ta3_state.time_, unstructured=ta3_state.unstructured)


def reverse_convert_state(tinymedstate: MedsimState) -> TA3State:
    cas = reverse_convert_casualties(tinymedstate.casualties)
    sup = reverse_convert_supplies(tinymedstate.supplies)
    ta3 = TA3State(casualties=cas, supplies=sup, unstructured=tinymedstate.unstructured, time_=int(tinymedstate.time),
                   actions_performed=list())
    return ta3


def _convert_action(act: Action) -> MedsimAction:
    supply, location = None, None
    if 'treatment' in act.params.keys():
        supply = act.params['treatment']
    if 'location' in act.params.keys():
        location = act.params['location']
    return MedsimAction(action=act.type, casualty_id=act.casualty,
                        supply=supply, location=location)


def _reverse_convert_action(internal_action: MedsimAction, action_num: int) -> Action:
    action: Action = Action(id='action_%d' % action_num, type=internal_action.action, casualty=internal_action.casualty_id,
                            kdmas={}, params={'casualty': internal_action.casualty_id,
                                              'location': internal_action.location,
                                              'treatment': internal_action.supply})
    return action
