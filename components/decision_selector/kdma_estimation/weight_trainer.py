from typing import Any
import math, pandas, numpy

from . import kdma_estimation
from .case_base_functions import integerish

from components.attribute_learner.xgboost import xgboost_train, data_processing
import util



class CaseModeller:
    def __init__(self):
        pass
        
    def adjust(self, weights: dict[str, float]):
        raise Error()

    def estimate_error(self) -> float:
        raise Error()
    
    def get_state(self) -> dict[str, Any]:
        raise Error()


class KEDSModeller(CaseModeller):
    cases: list[dict[str, Any]]
    last_error: float
    last_weights: dict[str, float]

    def __init__(self, cases: list[dict[str, Any]], kdma_name: str, partition_count: int = 10, avg = True):
        self.cases = cases
        self.last_error = None
        self.last_weights = None
        self.kdma_name = kdma_name
        self.case_partitions = []
        self.use_average_error = avg
        rcases = list(self.cases)
        util.get_global_random_generator().shuffle(rcases)
        part_size = len(rcases)//partition_count
        for i in range(partition_count):
            self.case_partitions.append(rcases[i*part_size:(i+1)*(part_size)])
        for i in range(partition_count * part_size, len(rcases)):
            part_num = i % partition_count
            self.case_partitions[part_num].append(rcases[i])

    def adjust(self, weights: dict[str, float]):
        self.last_weights = weights
        self.last_error = None

    def estimate_error(self) -> float:
        if self.last_error is None:
            self.last_error = kdma_estimation.find_leave_one_out_error(
                                                self.last_weights, self.kdma_name, 
                                                cases=self.cases, avg=self.use_average_error)
        return self.last_error
    
    def get_state(self) -> dict[str, Any]:
        return {"weights": self.last_weights, "error": self.estimate_error()}

class XGBModeller(CaseModeller):
    experience_data: pandas.DataFrame
    response_array: numpy.array
    category_array: numpy.array
    learning_style: str
    all_columns: list
    unique_values: list
    last_fields: set[str]
    last_weights: dict[str, float]
    last_error: float
    
    def __init__(self, cases: list[dict[str, Any]], kdma_name: str, learning_style = 'classification', ignore_patterns: list[str] = []):
        if len(cases) == 0:
            raise Error("Cannot create modeller without cases.")
        self.learning_style = learning_style
        experience_table = make_approval_data_frame(cases, kdma_name)
        if "index" in experience_table.columns:
            experience_table = experience_table.drop(columns=["index"])
        self.response_array = numpy.array(experience_table[kdma_name].tolist())
        self.all_columns = [col for col in experience_table.columns]
        self.all_columns.remove(kdma_name)
        self.last_fields = set()
        self.last_weights = dict()
        self.last_error = math.nan
        self.last_model = None

        # drop columns from table that we don't use, and those that are uninformative (all data the same)
        experience_table = xgboost_train.drop_columns_by_patterns(experience_table, label=kdma_name, patterns=ignore_patterns)
        experience_table = xgboost_train.drop_columns_if_all_unique(experience_table)
        if len(experience_table.columns) <= 1 or kdma_name not in experience_table.columns:
            print("Insufficient data to train weights.")
            self.experience_data = None
            self.category_array = None
            self.unique_values = []
            return

        self.experience_data = experience_table.drop(columns=[kdma_name])
        if learning_style == 'classification':
            self.unique_values = sorted(list(set(self.response_array)))
            self.category_array = numpy.array([self.unique_values.index(val) for val in self.response_array])

    def adjust(self, weights: dict[str, float]):
        if self.experience_data is None or len(weights) == 0:
            self.last_error = 10000
            self.last_weights = {}
            self.last_model = None
            self.last_fields = set()
            return
        fields = set(weights.keys())
        if fields != self.last_fields:
            self.refresh_model(fields)
        
    def estimate_error(self) -> float:
        return self.last_error

    def get_state(self) -> dict[str, Any]:
        return {"weights": self.last_weights, "error": self.last_error, "model": self.last_model}

    def refresh_model(self, fields: set[str]):
        X = self.get_subtable(fields)
        if len(X.columns) < 1:
            self.last_error = 10000
            self.last_weights = {}
            self.last_model = None
            self.last_fields = set()
            return
            
        if self.learning_style == 'regression':
            self.last_weights, self.last_error, self.last_model = \
                xgboost_train.get_regression_feature_importance(X, self.response_array)
        else:
            self.last_weights, self.last_error, model = \
                xgboost_train.get_classification_feature_importance(X, self.category_array)
            model.predict_right = lambda X: numpy.dot(self.unique_values, model.predict_proba(X)[0])
            self.last_model = model
        self.last_fields = set(fields)
    
    def get_subtable(self, fields: set[str]):
        unused = []
        for col in self.experience_data.columns:
            if col not in fields:
                unused.append(col)
        return self.experience_data.drop(columns = unused)

class KEDSWithXGBModeller(CaseModeller):
    kedsM: KEDSModeller
    xgbM: XGBModeller

    def __init__(self, cases: list[dict[str, Any]], kdma_name: str, learning_style = 'classification', ignore_patterns = []):
        self.kedsM = KEDSModeller(cases, kdma_name)
        self.xgbM = XGBModeller(cases, kdma_name, learning_style = learning_style, ignore_patterns = ignore_patterns)

    def adjust(self, weights: dict[str, float]):
        self.xgbM.adjust(weights)
        self.kedsM.adjust(self.xgbM.last_weights)

    def estimate_error(self) -> float:
        return self.kedsM.estimate_error()
    
    def get_state(self) -> dict[str, Any]:
        return self.kedsM.get_state()
        
        
class WeightQueue:
    feature_dict: dict[str, dict]
    
    def __init__(self, weight_dict: dict[str, float]):
        self.feature_dict = {k: {"weight": v, "removals": 0, "size_removed": 10000} for (k, v) in weight_dict.items()}
    
    def reinforce_feature(self, feature: str):
        self.feature_dict[feature]["removals"] += 1
        self.feature_dict[feature]["size_removed"] = len(self.feature_dict)
    
    def remove_feature(self, feature: str):
        self.feature_dict.pop(feature)
        
    def update_queue(self, weight_dict: dict[str, float]):
        new_dict = {}
        for k, v in self.feature_dict.items():
            if k in weight_dict:
                new_dict[k] = v
                v["weight"] = weight_dict[k]
        self.feature_dict = new_dict
    
    def top_feature(self):
        cur_size = len(self.feature_dict)
        min_removals = 10000
        min_weight = 10000
        best_feature = None
        for (feature, info) in self.feature_dict.items():
            if info["size_removed"] == cur_size:
                continue
            if info["removals"] > min_removals:
                continue
            if info["removals"] < min_removals:
                best_feature = feature
                min_removals = info["removals"]
                min_weight = info["weight"]
            elif info["weight"] < min_weight:
                best_feature = feature
                min_weight = info["weight"]
        return best_feature

class WeightTrainer:
    weight_error_hist: list[dict[str, Any]]
    best_error_index: int
    best_error: float
    modeller: CaseModeller
    fields: list[str]
    
    
    def __init__(self, modeller, fields):
        self.weight_error_hist = []
        self.best_error_index = None
        self.best_error = None
        self.modeller = modeller
        self.fields = fields

    def get_history(self):
        return self.weight_error_hist
        
    def get_best_weights(self):
        best_record = self.weight_error_hist[self.best_error_index]
        return best_record.get("name", best_record["weights"])
    
    def get_best_source(self):
        return self.weight_error_hist[self.best_error_index]["source"]

    def get_best_model(self):
        return self.weight_error_hist[self.best_error_index].get("model", None)

    def get_best_error(self):
        return self.weight_error_hist[self.best_error_index]["error"]
        
    def find_error(self, name: str):
        for record in self.weight_error_hist:
            if record.get("name", None) == name:
                return record["error"]
        raise Exception()
        
    def get_uniform_error(self): 
        return self.find_error("uniform")

    def get_basic_error(self): 
        return self.find_error("basic")

    def check_standard_weight_sets(self, standard_weight_sets: dict[str, dict[str, float]]):
        for (name, weight_set) in standard_weight_sets.items():
            self.add_to_history(weight_set, name = name, source = "standard")

    def weight_train(self, last_weights: dict[str, float]):
        self.weight_error_hist = []
        
        # add last weights tried to weight_error_hist
        if last_weights is not None and type(last_weights) != str and len(last_weights) > 0:
            self.add_to_history(last_weights, source = "last")
        
        last_weights = self.modeller.get_state()["weights"]
        queue = WeightQueue(last_weights)
        feature_to_remove = queue.top_feature()
        last_error = self.get_last_error()
        
        # Iteratively collect error data and drop another column, until the class column is all that's left.
        while feature_to_remove is not None:
            new_weights = dict(last_weights)
            new_weights.pop(feature_to_remove)
            print(f"Testing removal of feature {feature_to_remove}.")
            weights_modified = False

            # Record error and weights for modified feature set
            self.add_to_history(new_weights, source = "feature drop search")
            if new_weights != self.get_last_weights():
                weights_modified = True
                new_weights = self.get_last_weights()

            print(f"Last error: {last_error:0.2f} New error: {self.get_last_error():0.2f} New weight count: {len(new_weights)}")
            
            if self.weight_search_regressing(last_error):
                # Make this feature harder to remove
                queue.reinforce_feature(feature_to_remove)
                print(f"Weights regressed, {feature_to_remove} stays.")
            else:
                last_error = self.get_last_error()
                # Permanently remove the feature
                last_weights = new_weights
                print(f"Permanently removing {feature_to_remove}.")
                if weights_modified:
                    queue.update_queue(new_weights)
                else:
                    queue.remove_feature(feature_to_remove)
                    #TODO Try re-weighting

            # Pick a feature to try removing
            feature_to_remove = queue.top_feature()
    
        
    def weight_search_regressing(self, prior_error):
        last_error = self.get_last_error()
        if last_error > self.fudge_error(prior_error):
            return True
        return False
        

    def get_last_error(self):
        return self.weight_error_hist[-1].get("error", None)
    
    def get_last_weights(self):
        return self.weight_error_hist[-1].get("weights", None)

    def add_to_history(self, weights: dict[str, float], name: str = None, source: str = ""):
        self.modeller.adjust(weights)
        self.weight_error_hist.append(self.modeller.get_state())
        if name is not None:
            self.weight_error_hist[-1]["name"] = name
        self.weight_error_hist[-1]["source"] = source
        self.update_error()
            
    def update_error(self):
        new_error = self.get_last_error()
        new_index = len(self.weight_error_hist) - 1
        if self.best_error is None or math.isnan(self.best_error):
            self.best_error = new_error
            self.best_error_index = new_index
        elif new_error < self.best_error:
            self.best_error = new_error
            self.best_error_index = new_index
        elif new_error < self.fudge_error(self.best_error) \
             and (type(self.get_best_weights()) == str
                  or len(self.get_last_weights()) < len(self.get_best_weights())):
            self.best_error_index = new_index
    
    def fudge_error(self, error: float) -> float:
        return (error + .000001) * 1.01
        
        
def test_file_error(cb_fname: str, weights_dict: dict[str, float], kdma_name, drop_discounts = False, entries = None) -> float:
    seeker = get_test_seeker(cb_fname)
    table = make_approval_data_frame(seeker.cb, kdma_name, drop_discounts=drop_discounts, entries=entries)
    return seeker.find_weight_error(table, weights_dict)


def make_approval_data_frame(cases: list[dict[str, Any]], kdma_name, cols=None, drop_discounts = False, entries = None) -> pandas.DataFrame:
    cases = [dict(case) for case in cases if case.get(kdma_name, None) is not None]
    if drop_discounts:
        cases = [case for case in cases if integerish(10 * case[kdma_name])]
    if entries is not None:
        cases = cases[:entries]
    cleaned_experiences, category_labels = data_processing.clean_data(dict(zip(range(len(cases)), cases)))
    table = pandas.DataFrame.from_dict(cleaned_experiences, orient='index')
    if cols is not None:
        table = pandas.DataFrame(data=table, columns=cols)
    if "action" in table.columns:
        table = table.drop(columns=["action"])
    for col in table.columns:
        if col in category_labels:
            table[col] = table[col].astype('category')
    return table


