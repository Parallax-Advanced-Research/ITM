import random
from domain.internal import Scenario, TADProbe, Decision, KDMAs
from components import DecisionSelector


class HumanDecisionSelector(DecisionSelector):
    def select(self, _scenario: Scenario, probe: TADProbe, _target: KDMAs) -> (Decision, float):
        [print(f"{i}: {probe.decisions[i].value}") for i in range(len(probe.decisions))]
        decision: Decision = None
        while decision is None:
            text = input("Enter decision index: ").strip()
            if text.isnumeric():
                choice: int = int(text)
                if choice < 0 or choice >= len(probe.decisions):
                    print(text + " is not a valid selection.")
                decision: Decision = probe.decisions[choice]
            elif text.startswith("b"):
                breakpoint()
            else:
                print("Did not understand input: " + text)
        return decision, 1
