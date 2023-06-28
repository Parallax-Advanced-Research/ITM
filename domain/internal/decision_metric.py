from dataclasses import dataclass


class DecisionMetric:
    def __init__(self):
        self.metric_name = []
        self.analytic_attrs = []  # list of attributes


@dataclass
class Attribute:
    name: str
    desc: str
    value: str
