from domain.ta3.ta3_state import (Supply as TA_SUPPLY, Demographics as TA_DEM, Vitals as TA_VIT,
                                  Injury as TA_INJ, Casualty as TA_CAS, TA3State)
from .tinymed_enums import Demographics, Vitals, Injury, Casualty
from .tinymed_state import TinymedState


def _convert_demographic(ta_demographic: TA_DEM) -> Demographics:
    return Demographics(age=ta_demographic.age, sex=ta_demographic.sex, rank=ta_demographic.rank)


def _convert_vitals(ta_vitals: TA_VIT) -> Vitals:
    return Vitals(conscious=ta_vitals.conscious, mental_status=ta_vitals.mental_status,
                  breathing=ta_vitals.breathing, hrpmin=ta_vitals.hrpmin)


def _convert_injury(ta_injury: TA_INJ) -> Injury:
    return Injury(name=ta_injury.name, location=ta_injury.location, severity=ta_injury.severity)


def _convert_casualty(ta_casualty: TA_CAS) -> Casualty:
    dem = _convert_demographic(ta_casualty.demographics)
    injuries = []
    for inj in ta_casualty.injuries:
        injuries.append(_convert_injury(inj))
    vit = _convert_vitals(ta_casualty.vitals)

    return Casualty(id=ta_casualty.id, unstructured=ta_casualty.unstructured, name=ta_casualty.name,
                    relationship=ta_casualty.relationship, demographics=dem,injuries=injuries,
                    vitals=vit, complete_vitals=vit, assessed=ta_casualty.assessed, tag=ta_casualty.tag)


def convert_casualties(ta_casualties: list[TA_CAS]) -> list[Casualty]:
    casualties: list[Casualty] = []
    for cas in ta_casualties:
        casualties.append(_convert_casualty(cas))
    return casualties


def convert_supplies(ta_supplies: list[TA_SUPPLY]) -> dict[str, int]:
    supplies: dict[str, int] = {}
    for ta_sup in ta_supplies:
        supplies[ta_sup.type] = ta_sup.quantity
    return supplies


def convert_state(ta3_state: TA3State):
    cas = convert_casualties(ta3_state.casualties)
    sup = convert_supplies(ta3_state.supplies)
    return TinymedState(casualties=cas, supplies=sup, unstructured=ta3_state.unstructured)
