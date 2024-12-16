import math
from typing import Any, Sequence
from domain.internal import Scenario, TADProbe, KDMA, AlignmentTarget, Decision, Action, State
from domain.ta3 import TA3State, Casualty, Supply
from components import DecisionSelector, DecisionAnalyzer, Assessor
from triage import CompetenceAssessor
import util

class SeverityDecisionSelector(DecisionSelector):
    def __init__(self, args = None):
        self.competence_assessor = CompetenceAssessor()
        self.insert_pauses = False
        self.decision_verbose = False
        if args is not None:
            self.initialize_with_args(args)

    def initialize_with_args(self, args):
        self.insert_pauses = args.insert_pauses
        self.decision_verbose = args.decision_verbose


    def select(self, scenario: Scenario, probe: TADProbe, target: AlignmentTarget) -> (Decision, float):
        maxSeverityChange = -math.inf
        bestDecision = None
        competences = {}
        best_competence = None
        if self.competence_assessor is not None:
            competences = self.competence_assessor.assess(probe)
            best_competence = max(competences.values())

        for decision in probe.decisions:
            if self.decision_verbose:
                print(f"Decision: {decision.value}")
                print(f"Competence: {competences[str(decision.value)]}")
            if self.competence_assessor is not None and best_competence > competences[str(decision.value)]:
                # Just skip less competent actions.
                continue
            metric = decision.metrics.get("ACTION_TARGET_SEVERITY_CHANGE", None)
            if metric is not None:
                curChange = metric.value
                if curChange > maxSeverityChange:
                    maxSeverityChange = curChange
                    bestDecision = decision
                if self.decision_verbose:
                    print(f"Severity change: {curChange}")
                
                
        if bestDecision is None: 
            poss_decisions = probe.decisions
            if self.competence_assessor is not None:
                poss_decisions = [d for d in probe.decisions if competences[str(d.value)] == best_competence]
            bestDecision = util.get_global_random_generator().choice(poss_decisions)
            maxSeverityChange = "unknown"
        
        print(f"Selected action: {bestDecision.value}")
        if self.competence_assessor is not None:
            print(f"Competence: {competences[str(bestDecision.value)]}")
        print(f"Severity change: {maxSeverityChange}")
        if self.insert_pauses:
            breakpoint()
        return (bestDecision, maxSeverityChange)
        
    def add_assessor(self, name: str, assessor: Assessor):
        breakpoint()
        if name == "competence":
            self.competence_assessor = assessor

