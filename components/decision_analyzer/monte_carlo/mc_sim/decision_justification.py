import numpy as np
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Metric
from domain.internal import DecisionMetric


def return_metric_dict():
    return {
            Metric.MINIMUM.value: None,
            Metric.MAXIMUM.value: None,
            Metric.MEAN.value: None,
            Metric.RANK_ORDER.value: None,
            Metric.RANK_TOTAL.value: None
        }


def get_numeric(val_idx):
    if val_idx in [10, 11, 12, 13]:
        return 'th'
    last_digit = str(val_idx)[-1]
    if last_digit in ['0','1']:
        return 'st'
    if last_digit == '2':
        return 'nd'
    if last_digit == '3':
        return 'rd'
    return 'th'


def get_ranked_title(ranking_list: list[float], val: DecisionMetric, reverse=False) -> tuple:
    relevant_list = ranking_list['all']
    if reverse:
        relevant_list = sorted(relevant_list, reverse=True)
    val_idx = relevant_list.index(val.value) + 1
    is_tie = True if relevant_list.count(val.value) > 1 else False
    return "%s%d%s" % ('T-' if is_tie else '', val_idx, get_numeric(val_idx)), len(relevant_list)


class DecisionJustifier:
    def __init__(self, dict_values):
        self.values = dict_values
        self.metric_names = list(self.values.keys())
        self.analyzed_values: dict[str, dict[str, float]] = dict()
        self._analyze()

    def get_metric_names(self):
        return self.metric_names

    def _analyze(self):
        for metric in self.metric_names:
            vals = self.values[metric]
            if isinstance(vals[0], dict):
                continue  # Nondeterministic outcomes were already averaged, not needed
            lex_arr = np.random.random(np.array(vals).size)
            self.analyzed_values[metric] = {
                'all': sorted(vals),
                Metric.MINIMUM.value: min(vals),
                Metric.MAXIMUM.value: max(vals),
                Metric.MEAN.value: np.mean(vals),
                Metric.N_ROLLOUTS.value: len(vals)
            }

    def generate_justification(self, metric_name: str, metric_val: DecisionMetric, decision_name: str) -> str:
        if metric_name not in self.analyzed_values:
            return ''
        reverseables = [Metric.SUPPLIES_REMAINING.value]
        reverse = True if metric_name in reverseables else False
        ranked_title, total = get_ranked_title(self.analyzed_values[metric_name], metric_val, reverse)
        retstr = "%s Metrics for Decision %s is %s/%d in ranking. Val = %.1f, (Range %.1f - %.1f, avg %.1f)." % (metric_name, decision_name,
                                                                                                      ranked_title, total,
                                                                                                      metric_val.value,
                                                                                                      self.analyzed_values[metric_name][Metric.MINIMUM.value],
                                                                                                      self.analyzed_values[metric_name][Metric.MAXIMUM.value],
                                                                                                      self.analyzed_values[metric_name][Metric.MEAN.value])
        return retstr

    def generate_justification_json(self, metric_name: str, metric_val: DecisionMetric, decision_name: str) -> dict[str, int | float]:
        if metric_name not in self.analyzed_values:
            return {Metric.N_ROLLOUTS.value: 0}
        reverseables = [Metric.SUPPLIES_REMAINING.value]
        reverse = True if metric_name in reverseables else False
        ranked_title, total = get_ranked_title(self.analyzed_values[metric_name], metric_val, reverse)
        return {
            Metric.METRIC_NAME.value: metric_name,
            Metric.ACTION_NAME.value: decision_name,
            Metric.DECISION_VALUE.value: metric_val.value,
            Metric.MINIMUM.value: self.analyzed_values[metric_name][Metric.MINIMUM.value],
            Metric.MAXIMUM.value: self.analyzed_values[metric_name][Metric.MAXIMUM.value],
            Metric.MEAN.value: self.analyzed_values[metric_name][Metric.MEAN.value],
            Metric.RANK_ORDER.value: int(''.join(c for c in ranked_title if c.isdigit())),
            Metric.RANK_TOTAL.value: total,
            Metric.IS_TIED.value: 'T' in ranked_title
        }
