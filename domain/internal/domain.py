from . import Decision, Action, StateType, TADProbe
from .kdmas import KDMAs
import typing

class Domain:
    def make_decision(
            self, id_: str, action_type: str, params: dict[str, typing.Any],
            kdmas: KDMAs, intend: bool) -> Decision[Action]:
        return Decision(id_, Action(action_type, params), [],[], None, kdmas, intend)

    def update_decision_parameters(
                d: Decision, params: dict[str, typing.Any]) -> Decision[Action]:
        return Decision(d.id_, Action(d.value.name, params.copy()), d.justifications, d.explanations, d.metrics, d.kdmas, d.intend)

    def make_probe(
            self, id_: str, state: StateType, prompt: str, environment: dict = {},
            decisions: list[Decision] = ()) -> TADProbe:
        return TADProbe(id_, state, prompt, environment, decisions)

    def has_special_features(self) -> bool:
        return False

    def add_special_features(self, case: dict, probe: TADProbe, d: Decision, variant: str) -> dict[str, typing.Any]:
        raise Error("Base domain adds no special features.")
