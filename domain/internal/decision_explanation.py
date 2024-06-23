from dataclasses import dataclass
import typing

from domain.internal.decision_metric import DecisionMetric, DecisionMetrics, DecisionName
from domain.internal.justification import Justification
from domain.internal.kdmas import KDMAs
from util.dict_tools import Dict_No_Overwrite

T = typing.TypeVar('T')

class Explanation():
    def __init__(self, name: str, vals: dict[str, typing.Any]):
        self.name: str = name
        self.vals: dict[str, typing.Any] = vals

class DecisionExplanation():
    def __init__(self, name: str, description: str):
        # the parts of the decision that are involved in the explanation
        # there can be multiple explanations, one for each decision type (KDMA, etc.)
        self.name = name        
        self.description: str = description
        self.explanations = list[Explanation]()
        
              
    def get_formatted_explanation(self):
        # serialize the explanations so we can save them to a file
        explanation_list = []
        for explanation in self.explanations:
            explanation_list.append(explanation.vals)
        
        return explanation_list


