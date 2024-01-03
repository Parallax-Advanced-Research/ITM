import itertools
import json
import random
import copy
import numbers
from domain.internal import TADProbe, Scenario, Decision, DecisionMetrics, DecisionMetric
from components import DecisionAnalyzer
from typing import List, Tuple, Union, Dict, Any, Optional

SelectedTreatment = Union[
    Tuple[str, dict, str]
]

TreatmentComparison = Union[
    Tuple[bool, bool]
]

# currently runs for set of possible decisions, future may change to be called for each decision
class HeuristicRuleAnalyzer(DecisionAnalyzer):
    STRATEGIES = ["take-the-best", "exhaustive", "tallying", "satisfactory", "one-bounce"]

    def __init__(self):
        super().__init__()

    # make all permutations of decision pairs based on their list index 
    def make_dspace_permutation_pairs(self, obj_cnt:int):
        if not isinstance(obj_cnt, numbers.Number): raise AttributeError("Incorrect arg types or size")
        dsize = int((obj_cnt) * (obj_cnt - 1) / 2)
        d = list()

        for i in range(obj_cnt):
            for j in range(i, -1, -1):
                if i != j:
                    d.append((i, j))

        if len(d) == dsize:
            return d
        else:
            raise Exception("error, size mismatch")

    ''' Given the maximal predictor set with values, generate all combination sets of size set_sz

        inputs: 
        - predictor_set_arg, the maximal predictor set
        - set_sz, the size of each combination set returned

        outputs:
        - a list of all predictor combination dictionaries
    '''

    def gen_predictor_combo(self, predictor_set_arg: dict, set_sz: int):

        if type(predictor_set_arg) != dict or type(set_sz) != int or set_sz < 0 or set_sz > len(predictor_set_arg): raise AttributeError("Incorrect arg types or size")
        results = itertools.combinations(predictor_set_arg, set_sz)
        all_predictors_sets = []
        for predictor_set in results:
            pred_dict = {predictor_set[p]: predictor_set_arg[predictor_set[p]] for p in range(len(predictor_set))}
            all_predictors_sets.append(pred_dict)

        return all_predictors_sets

    ''' Given a treatment pair compare them according to kma predictor values
    
        inputs:
        - predictor_key, the key in the predictor dict
        - predictor_val, the value in the predictor dict
        - system, the casualty injury impacted system
        - treatment0, the value from treatment dict for first treatment
        - treatment1, the value from treatment dict for second treatment
        
        outputs:
        - tuple (True/False, True/False), with True if the treatment predictor val matched the kdm predictor val
    '''
    def compare_treatment_pair(self, predictor_key:str, predictor_val, system:str, treatment0:dict, treatment1:dict)-> TreatmentComparison:
        if type(predictor_key) != str or type(system) != str or type(treatment0) != dict or type(treatment1) != dict: \
                raise AttributeError("argument type mismatch")
        if not (predictor_key in treatment0 and predictor_key in treatment1): raise KeyError("Predictor doesn't exist for treatment")

        result0 = False
        result1 = False

        if predictor_key == "system":
            result0 = treatment0[predictor_key] == predictor_val or treatment0[predictor_key] == "all"
            result1 = treatment1[predictor_key] == predictor_val or treatment1[predictor_key] == "all"

        else:
            result0 = treatment0[predictor_key] == predictor_val
            result1 = treatment1[predictor_key] == predictor_val

        return result0, result1

    '''
    Take-the-best: Given a set of predictors ranked by validity, and n treatments in the decision space, return the treatment that performs 
    best in terms of its predictor values matching with kdm predictor values. In the case where there are multiple highest 
    performing treatments, return "no preference". The comparisons are performed among Σ(n-1) treatment pairs, with each 
    treatment compared to every other treatment once. A comparison stops after the first predictor that discriminates.

    input: 
    - file_name: json file with scenario, predictors, casualty, and treatment info, where predictors preferences are ranked according to validity
    - data: a dictionary with the same info as file_name that may used instead of file_name

    output:
    - decision
    '''

    def take_the_best(self, file_name: str, search_path=False, data: dict = None) -> SelectedTreatment:

        if (type(file_name) != str or len(file_name) == 0) and (type(data) != dict or data is None): raise AttributeError(
            "No info to process")

        # prep the input
        if data is None:
            with open(file_name, 'r') as f:
                data = json.load(f)
        treatment_idx = list(data['treatment'])

        # if there is only a single treatment in the decision space
        if len(treatment_idx) == 1:
            return treatment_idx[0], data['treatment'][treatment_idx[0]], ""
        elif len(treatment_idx) == 0:
            return "no preference", {}, ""

        # if search_path then return as part of output the order of pairs and their scores
        search_tree = str()

        # generate permutations of comparisons between treatments
        treatment_pairs = self.make_dspace_permutation_pairs(len(treatment_idx))

        # create container to hold number of comparisons won for each treatment
        treatment_sums = [0] * len(treatment_idx)

        # iterate through treatment pairs
        for tpair in treatment_pairs:
            treatment0 = data['treatment'][treatment_idx[tpair[0]]]
            treatment1 = data['treatment'][treatment_idx[tpair[1]]]

            # - for each predictor, compare treatment and predictor values
            for predictor in data['predictors']['relevance']:
                predictor_val = data['predictors']['relevance'][predictor]

                compare_result = self.compare_treatment_pair(predictor, predictor_val, data['casualty']['injury']['system'], treatment0, treatment1)
                if compare_result[0] and not compare_result[1]:
                    treatment_sums[tpair[0]] += 1
                    search_tree += ",".join([treatment_idx[tpair[0]], str(treatment_sums[tpair[0]]), treatment_idx[tpair[1]], str(treatment_sums[tpair[1]])])
                    break
                elif compare_result[1] and not compare_result[0]:
                    treatment_sums[tpair[1]] += 1
                    search_tree += ",".join([treatment_idx[tpair[0]], str(treatment_sums[tpair[0]]), treatment_idx[tpair[1]], str(treatment_sums[tpair[1]])])
                    break

        # if there is an overall winner, return it
        max_val = max(treatment_sums)
        sequence = range(len(treatment_sums))
        list_indices = [index for index in sequence if treatment_sums[index] == max_val]

        # - if there is no tie, the treatment with the max value wins, else return "no preference"
        if len(list_indices) == 1:
            return treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]], search_tree
        else:
            return "no preference", {}, search_tree

    '''Returns the highest priority casualty according to cues used by take-the-best

    input:
    - casualty_dict: dictionary of casualties
    - kdma_list: list of kdmas with their values

    output:
    - casualty id as string
    '''

    def take_the_best_priority(self, casualty_dict: dict, kdma_list: dict) -> dict:

        if len(casualty_dict) == 0: raise Exception("no casualties exist")
        if type(casualty_dict) != dict or type(kdma_list) != dict: raise AttributeError("Incorrect arg types or size")
        if len(kdma_list) == 0: raise Exception("there are no kdmas")

        # get kdma with highest value
        max_kdma = max(zip(kdma_list.values(), kdma_list.keys()))[1]

        # create table of casualty fields to worth
        casualty_val_table = dict()
        casualty_val_table['relationship'] = {'same-unit': 1, 'friend': 2}
        casualty_val_table['rank'] = {'civilian': 0, 'marine': 1, 'intel officer': 2, 'vip': 3}

        # hold sums for each casualty
        casualty_sum = dict()

        for person, info in casualty_dict.items():
            casualty_sum[person] = 0
            match max_kdma:  # do try here
                case 'mission':
                    casualty_sum[person] += 0 if info['demographics']['rank'] is None else casualty_val_table['rank'][
                        info['demographics']['rank'].lower()]
                case 'denial':
                    casualty_sum[person] += 0 if info['relationship'] == 'NONE' else casualty_val_table['relationship'][
                        info['relationship'].lower()]
                case _:
                    raise Exception("invalid kdma")

        # return casualty ranked highest
        max_casualty = max(zip(casualty_sum.values(), casualty_sum.keys()))[1]
        return {max_casualty: casualty_dict[max_casualty]}  # returns first casualty with max score

    '''
    Exhaustive: Search strategy that ranks ALL decisions in decisions space according to 
    ALL relevance predictor values and returns the highest ranked treatment

    input: 
    - file_name: json file that describes scenario, predictor, casualty, and decision space
    - data: a dictionary with the same info as file_name that may used instead of file_name

    output:
    - decision
    '''

    def exhaustive(self, file_name: str, search_path=False, data: dict = None) -> SelectedTreatment:

        if (type(file_name) != str or len(file_name) == 0) and (type(data) != dict or data is None): raise AttributeError(
            "No info to process")

        if data is None:
            with open(file_name, 'r') as f:
                data = json.load(f)
        treatment_idx = list(data['treatment'])

        # if there is only a single treatment in the decision space
        if len(treatment_idx) == 1:
            return treatment_idx[0], data['treatment'][treatment_idx[0]], ""
        elif len(treatment_idx) == 0:
            return "no preference", {}, ""

        # create corresponding array to hold treatment scores
        all_treatment_sum = list()
        treatment_sum = 0

        for treatment in treatment_idx:

            # - for each predictor in set check its value against that of the predictor
            for predictor in data['predictors']['relevance']:
                predictor_val = data['predictors']['relevance'][predictor]

                # - - if the value matches, add 1 to the treatment sum
                # - - - special case for system predictor
                if predictor == "system":
                    if data['treatment'][treatment][predictor] == data['casualty']['injury']['system'] or \
                            data['treatment'][treatment][predictor] == "all":
                        treatment_sum += 1

                # - - - normal case for predictor
                else:
                    if data['treatment'][treatment][predictor] == predictor_val:
                        treatment_sum += 1

            all_treatment_sum.append(treatment_sum)
            treatment_sum = 0

        # store search order
        search_tree = ','.join(treatment_idx[i] + ',' + str(all_treatment_sum[i]) for i in range(len(treatment_idx)))

        # return treatment with max sum
        max_val = max(all_treatment_sum)
        sequence = range(len(all_treatment_sum))
        list_indices = [index for index in sequence if all_treatment_sum[index] == max_val]

        # - if the max isn't tied, else return "no preference"
        if len(list_indices) == 1:
            return treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]], search_tree
        else:
            return "no preference", {}, search_tree

    '''Returns the highest priority casualty according to cues used by exhaustive

    input:
    - dictionary of casualties

    output:
    - casualty id as string
    '''

    def exhaustive_priority(self, casualty_dict: dict) -> dict:

        if len(casualty_dict) == 0: raise Exception("no casualties exist")
        if type(casualty_dict) != dict: raise AttributeError("Incorrect arg types or size")

        # create table of casualty fields to worth
        casualty_val_table = dict()
        casualty_val_table['relationship'] = {'same-unit': 1, 'friend': 2}
        casualty_val_table['rank'] = {'civilian': 0, 'marine': 1, 'intel officer': 2, 'vip': 3}

        # hold sums for each casualty
        casualty_sum = dict()

        for person, info in casualty_dict.items():

            casualty_sum[person] = 0
            casualty_sum[person] += 0 if info['demographics']['rank'] is None else casualty_val_table['rank'][
                info['demographics']['rank'].lower()]
            casualty_sum[person] += 0 if info['relationship'] == 'NONE' else casualty_val_table['relationship'][
                info['relationship'].lower()]
            casualty_sum[person] += 0 if info['demographics']['age'] is None else (
                1 if (0 <= info['demographics']['age'] <= 10 or 65 <= info['demographics']['age'] <= 100) else 0)
            for injury in info['injuries']:
                if isinstance(injury['severity'], float):
                    if 0.5 <= injury['severity'] <= 1: casualty_sum[person] += 1

        # return highest ranked casualty
        max_casualty = max(zip(casualty_sum.values(), casualty_sum.keys()))[1]
        return {max_casualty: casualty_dict[max_casualty]}

    '''
    Tallying: Given a set of randomly selected predictors m, where m ⊆ M (the complete set of predictors), and n treatments 
    in the decision space, return the treatment that performs best in terms of its predictor values matching with kdm 
    predictor values. The comparisons are performed among Σ(n-1) treatment pairs, with each treatment compared to every other 
    treatment once. If one treatment performs better add 1 to its sum and continue to the next treatment pair. If two 
    treatments perform equally with respect to the set m, and |m| < |M|, randomly select one of the 
    remaining predictors from M, comparing the treatment pair against this new predictor; if |m| == |M|, 
    continue to the next treatment pair. Return the treatment that performed best relative to the other treatments, or 
    "no preference" if there no clear winner.

    input: 
    - file_name: json file that describes scenario, predictor, casualty, and decision space
    - data: a dictionary with the same info as file_name that may used instead of file_name
    - m, where 0 < m <= M, is the size of the set of predictors to consider when comparing 2 treatments

    output: decision
    '''

    def tallying(self, file_name: str, m: int, seed=None, search_path=False, data: dict = None) -> SelectedTreatment:

        if (type(file_name) != str or len(file_name) == 0) and (type(data) != dict or data is None): raise AttributeError(
            "No info to process")
        if not (isinstance(m, numbers.Number) and m > 0): raise AttributeError("Bad value for m")

        # set random seed
        if seed is not None:
            random.seed(seed)

        # prep inputs
        if data is None:
            with open(file_name, 'r') as f:
                data = json.load(f)
        treatment_idx = list(data['treatment'])

        # if there is only a single treatment in the decision space
        if len(treatment_idx) == 1:
            return treatment_idx[0], data['treatment'][treatment_idx[0]], ""
        elif len(treatment_idx) == 0:
            return "no preference", {}, ""

        # return as part of output the order of pairs and their scores
        search_tree = str()

        # select random set of m predictors
        predictor_idx = list(data['predictors']['relevance'])

        # - get m random indices for predictors
        rand_predictor_idx = random.sample(range(0, len(predictor_idx)), len(predictor_idx))

        # prepare variables for comparisons
        treatment_pairs = self.make_dspace_permutation_pairs(len(treatment_idx))

        # - create container to hold number of comparisons won for each treatment
        treatment_sums = [0] * len(treatment_idx)

        # - create container to hold number of predictors matched for each treatment
        treatment_predictor_sums = [0] * 2

        for tpair in treatment_pairs:
            treatment0 = data['treatment'][treatment_idx[tpair[0]]]
            treatment1 = data['treatment'][treatment_idx[tpair[1]]]
            treatment_predictor_sums[0] = treatment_predictor_sums[1] = 0

            # - - for each predictor, compare treatment and predictor values
            for h in rand_predictor_idx[:m]:
                predictor = predictor_idx[h]
                predictor_val = data['predictors']['relevance'][predictor]

                compare_result = self.compare_treatment_pair(predictor, predictor_val, data['casualty']['injury']['system'], treatment0, treatment1)
                treatment_predictor_sums[0] += 1 if compare_result[0] else 0
                treatment_predictor_sums[1] += 1 if compare_result[1] else 0

            # get the round winner
            if treatment_predictor_sums[0] != treatment_predictor_sums[1]:

                # - - - add one to treatment score of treatment with max sum
                treatment_sums[tpair[0] if treatment_predictor_sums[0] > treatment_predictor_sums[1] else tpair[1]] += 1
                if len(search_tree) > 0: search_tree += ","
                search_tree += ",".join(
                    [treatment_idx[tpair[0]], str(treatment_predictor_sums[0]), treatment_idx[tpair[1]], str(treatment_predictor_sums[1])])

            else:
                # - - - get M\m set of random predictors
                rrand_predictor_idx = rand_predictor_idx[m:]

                # - - - while size of set M\m is not empty
                for i in rrand_predictor_idx:
                    rpredictor = predictor_idx[i]
                    rpredictor_val = data['predictors']['relevance'][rpredictor]

                    rcompare_result = self.compare_treatment_pair(rpredictor, rpredictor_val, data['casualty']['injury']['system'], treatment0, treatment1)
                    treatment_predictor_sums[0] += 1 if rcompare_result[0] else 0
                    treatment_predictor_sums[1] += 1 if rcompare_result[1] else 0

                    # - - - - get the round winner
                    if treatment_predictor_sums[0] != treatment_predictor_sums[1]:

                        # - - - - - - add one to treament score of treatment with max sum and continue to next treatment pair
                        treatment_sums[
                            tpair[0] if treatment_predictor_sums[0] > treatment_predictor_sums[1] else tpair[1]] += 1

                        if len(search_tree) > 0: search_tree += ","
                        search_tree += ",".join([treatment_idx[tpair[0]], str(treatment_predictor_sums[0]), treatment_idx[tpair[1]], str(treatment_predictor_sums[1])])
                        break

        # return a decision
        max_val = max(treatment_sums)
        sequence = range(len(treatment_sums))
        list_indices = [index for index in sequence if treatment_sums[index] == max_val]

        # - if there is no tie, the treatment with the max value wins, else return "no preference"
        if len(list_indices) == 1:
            return treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]], search_tree
        else:
            return "no preference", {}, search_tree

    '''Returns the highest priority casualty according to cues used by tallying

    input:
    - casualty_dict: dictionary of casualties
    - m: the number of casualty features to consider

    output:
    - casualty id and info as dict
    '''

    def tallying_priority(self, casualty_dict: dict, m: int = 4) -> dict:

        if type(casualty_dict) != dict: raise AttributeError("Incorrect arg types or size")
        if len(casualty_dict) == 0: raise Exception("no casualties exist")
        if type(m) != int or m <= 0: raise Exception("A positive integer number of predictors must be considered")

        # create table of casualty fields to worth
        casualty_val_table = dict()
        casualty_val_table['relationship'] = {'same-unit': 1, 'friend': 1}
        casualty_val_table['rank'] = {'civilian': 1, 'marine': 1, 'intel officer': 1, 'vip': 1}

        # variables for checking each casualty
        casualty_sum = dict()

        for person, info in casualty_dict.items():
            casualty_sum[person] = 0
            cnt = 0  # stays <= m

            if cnt >= m: continue
            casualty_sum[person] += 0 if info['relationship'] == 'NONE' else casualty_val_table['relationship'][
                info['relationship'].lower()]
            cnt += 1
            if cnt >= m: continue
            casualty_sum[person] += 0 if info['demographics']['rank'] is None else casualty_val_table['rank'][
                info['demographics']['rank'].lower()]
            cnt += 1
            if cnt >= m: continue
            casualty_sum[person] += 0 if info['demographics']['age'] is None else (
                1 if (0 <= info['demographics']['age'] <= 10 or 65 <= info['demographics']['age'] <= 100) else 0)
            cnt += 1
            if cnt >= m: continue
            for injury in info['injuries']:
                if isinstance(injury['severity'], float):
                    if 0.5 <= injury['severity'] <= 1: casualty_sum[person] += 1

        # return the first occurrence of the highest ranked casualty
        max_casualty = max(zip(casualty_sum.values(), casualty_sum.keys()))[1]
        return {max_casualty: casualty_dict[max_casualty]}

    '''
    Satisfactory: Given a set of randomly selected predictors m, where m ⊆ M (the complete set of predictors),
    and n treatments in the decision space, return the treatment that performs best in terms of its predictor values
    matching with kdm associated predictor values. The comparisons are performed among Σ(n-1) treatment pairs,
    with each treatment compared to every other treatment once. A comparison stops after the first predictor that discriminates.
    If two treatments perform equally with respect to the set m, and the size of m < the size of M, randomly select one of the
    remaining predictors from M comparing the treatment pair against this new predictor; if the size of m equals that of M,
    continue to the next treatment pair. Return the treatment that performed best relative to the other treatments, or
    "no preference" if there no clear winner.
    
    input: 
    - file_name: json file that describes scenario, predictor, casualty, and decision space
    - data: a dictionary with the same info as file_name that may used instead of file_name
    - m, where 0 < m <= M, is the size of the set of predictors to consider when comparing 2 treatments

    output: 
    - decision
    '''
    def satisfactory(self, file_name: str, m: int, seed=None, data: dict=None) -> SelectedTreatment:

        if (type(file_name) is not str or len(file_name) == 0) and (type(data) is not dict or data is None): raise AttributeError(
            "No info to process")
        if not (isinstance(m, numbers.Number) and m > 0): raise AttributeError("Bad value for m")

        # set random seed
        if seed is not None:
            random.seed(seed)

        # prep inputs
        if data is None:
            with open(file_name, 'r') as f:
                data = json.load(f)
        treatment_idx = list(data['treatment'])

        # if there is only a single treatment in the decision space
        if len(treatment_idx) == 1:
            return treatment_idx[0], data['treatment'][treatment_idx[0]], ""
        elif len(treatment_idx) == 0:
            return "no preference", {}, ""

        # return as part of output the order of pairs and their scores
        search_tree = str()

        # select random set of m predictors
        predictor_idx = list(data['predictors']['relevance'])
        rand_predictor_idx = random.sample(range(0, len(predictor_idx)), len(predictor_idx))

        # prepare variables for comparisons
        treatment_pairs = self.make_dspace_permutation_pairs(len(treatment_idx))

        # - create container to hold number of comparisons won for each treatment
        treatment_sums = [0] * len(treatment_idx)

        # do comparisons between treatments
        for tpair in treatment_pairs:
            treatment0 = data['treatment'][treatment_idx[tpair[0]]]
            treatment1 = data['treatment'][treatment_idx[tpair[1]]]
            winner = False

            # - - for each predictor, compare treatment and predictor values
            for h in rand_predictor_idx[:m]:
                predictor = predictor_idx[h]
                predictor_val = data['predictors']['relevance'][predictor]

                compare_result = self.compare_treatment_pair(predictor, predictor_val, data['casualty']['injury']['system'], treatment0, treatment1)
                if compare_result[0] and not compare_result[1]:
                    treatment_sums[tpair[0]] += 1
                    search_tree += ",".join([treatment_idx[tpair[0]], str(treatment_sums[tpair[0]]), treatment_idx[tpair[1]], str(treatment_sums[tpair[1]])])
                    winner = True
                    break
                elif compare_result[1] and not compare_result[0]:
                    treatment_sums[tpair[1]] += 1
                    search_tree += ",".join([treatment_idx[tpair[0]], str(treatment_sums[tpair[0]]), treatment_idx[tpair[1]], str(treatment_sums[tpair[1]])])
                    winner = True
                    break

            # get the round winner
            # - - if the two treatment scores are not equal or else they are
            if winner:
                continue
            else:
                # - - - get M\m set of random predictors
                rrand_predictor_idx = rand_predictor_idx[m:]

                # - - - while size of set M\m is not empty
                for i in rrand_predictor_idx:
                    rpredictor = predictor_idx[i]
                    rpredictor_val = data['predictors']['relevance'][rpredictor]

                    rcompare_result = self.compare_treatment_pair(rpredictor, rpredictor_val, data['casualty']['injury']['system'], treatment0, treatment1)
                    if rcompare_result[0] and not rcompare_result[1]:
                        treatment_sums[tpair[0]] += 1
                        search_tree += ",".join(
                            [treatment_idx[tpair[0]], str(treatment_sums[tpair[0]]), treatment_idx[tpair[1]], str(treatment_sums[tpair[1]])])
                        break
                    elif rcompare_result[1] and not rcompare_result[0]:
                        treatment_sums[tpair[1]] += 1
                        search_tree += ",".join(
                            [treatment_idx[tpair[0]], str(treatment_sums[tpair[0]]), treatment_idx[tpair[1]], str(treatment_sums[tpair[1]])])
                        break

        # return a decision
        max_val = max(treatment_sums)
        sequence = range(len(treatment_sums))
        list_indices = [index for index in sequence if treatment_sums[index] == max_val]

        # - if there is no tie, the treatment with the max value wins, else return "no preference"
        if len(list_indices) == 1:
            return treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]], search_tree
        else:
            return "no preference", {}, search_tree

    '''Returns the highest priority casualty according to cues used by satisfactory

    input:
    - dictionary of casualties

    output:
    - casualty id as string
    '''
    def satisfactory_priority(self, casualty_dict: dict) -> dict:

        if type(casualty_dict) != dict: raise AttributeError("Incorrect arg types or size")
        if len(casualty_dict) == 0: raise Exception("no casualties exist")

        # current highest priority characteristics, TODO: will change with kdmas
        for person, info in casualty_dict.items():
            if info['demographics']['rank'].lower() == 'vip':
                for injury in info['injuries']:
                    if isinstance(injury['severity'], float):
                        if 0 <= injury['severity'] <= 1: return {person: info}

        # if no casualty that satisfies requirements return first in list
        return {list(casualty_dict.keys())[0]:list(casualty_dict.values())[0]}

    '''
    One-Bounce: If there is a randomly ordered sequence of decisions, when two decisions are compared against all predictors,
    if the heuristic (partial calculation with tallying over fixed, ranked, deterministic set m) indicates that the winner will not change in the next
    (0 to k) comparisons where k ⊆ of K (the complete set of possible treatments), stop and take the winner. Otherwise,
    immediately stop the 0 to k comparisons and repeat the process with a comparison on M predictors between the current winner and
    the new potential winner, again checking (0 to k) treatments ahead. The comparisons are performed among Σ(n-1) treatment pairs,
    with each treatment compared to every other treatment at most twice (once with m predictors, and again with M predictors).
    If no treatment is returned via the above process return "no preference".

    input:
    - file_name: json file that describes scenario, kdmas, casualty, RANKED predictors, and treatment info
    - data: a dictionary with the same info as file_name that may used instead of file_name
    - m, where 0 < m <= M predictors to consider when comparing 2 treatments
    - k, where 0 < k <= K, perform tallying on present winner with up to k other treatments

    output: decision
    '''
    def one_bounce(self, file_name: str, m: int, k: int, search_path=False, data: dict = None) -> SelectedTreatment:

        if (type(file_name) != str or len(file_name) == 0) and (type(data) != dict or data is None): raise AttributeError(
            "No info to process")
        if not ((isinstance(m, numbers.Number) and m > 0) or isinstance((k, numbers.Number) and k > 0)): raise AttributeError(
            "Bad value for k or m")

        # prep the input
        if data is None:
            with open(file_name, 'r') as f:
                data = json.load(f)
        treatment_idx = list(data['treatment'])

        # if there is only a single treatment in the decision space
        if len(treatment_idx) == 1:
            return treatment_idx[0], data['treatment'][treatment_idx[0]], ""
        elif len(treatment_idx) == 0:
            return "no preference", {}, ""

        # return as part of output the order of pairs and their scores
        search_tree = str()

        # generate permutations of comparisons between treatments and containers to hold the result
        treatment_pairs = self.make_dspace_permutation_pairs(
            len(treatment_idx))
        treatment_sums = [0] * len(treatment_idx)  # NOTE: do we need this? think not
        treatment_predictor_sums = [0] * 2

        # store comparison pairs in list e.g. list[list] -> tpair[0] = [(1,0), (2,0), (3,0), (4,0)], tpair[1] = [(2,1), (3,1), (4,1)] ... tpair[4] = []
        tpair = [None] * len(treatment_idx)
        for ele in treatment_pairs:
            first = ele[1]
            if tpair[first] is None:
                tpair[first] = list()
                tpair[first].append((ele[1], ele[0]))
            else:
                tpair[first].append((ele[1], ele[0]))
        tpair[-1] = list()

        # loop through tpair
        cnt = len(treatment_pairs)
        winner_idx = None
        tpair_idx = None
        if len(tpair) >= 1:
            if len(tpair[0]) >= 1:
                winner_idx = 0
                tpair_idx = 0
        else:
            raise Exception("No treatments to compare")

        # continue checking tpairs, while number of tpair < num of comparison pairs
        while (cnt > 0):
            cnt -= 1
            # - do main tpair
            pair = tpair[winner_idx][tpair_idx]
            treatment0 = data['treatment'][treatment_idx[pair[0]]]
            treatment1 = data['treatment'][treatment_idx[pair[1]]]
            treatment_predictor_sums[0] = treatment_predictor_sums[1] = 0

            # - - iterate through each of M predictors
            for predictor in data['predictors']['relevance']:
                predictor_val = data['predictors']['relevance'][predictor]

                compare_result = self.compare_treatment_pair(predictor, predictor_val, data['casualty']['injury']['system'], treatment0, treatment1)
                treatment_predictor_sums[0] += 1 if compare_result[0] else 0
                treatment_predictor_sums[1] += 1 if compare_result[1] else 0

            # get the round winner
            # - if winner wins
            if treatment_predictor_sums[0] > treatment_predictor_sums[1]:
                # - - if winner has no more tpair elements
                if tpair_idx >= len(tpair[winner_idx]) - 1:

                    search_tree += ",".join(
                        [treatment_idx[pair[0]], str(treatment_predictor_sums[0]), treatment_idx[pair[1]],
                         str(treatment_predictor_sums[1])])
                    return treatment_idx[pair[0]], treatment0, search_tree

                # - - if winner has more tpair pairs
                elif tpair_idx < len(tpair[winner_idx]) - 1:  # got some stuff to do
                    tpair_idx += 1

            # - if winner and fighter are equal continue to next set of pairs
            elif treatment_predictor_sums[0] == treatment_predictor_sums[1]:
                if winner_idx < len(
                        tpair) - 1:  # NOTE: find better future solution, although they tie, they could have the highest predictors sums of all pairs
                    winner_idx += 1
                    if len(tpair[winner_idx]) >= 1:
                        tpair_idx = 0
                        continue
                    else:
                        return "no preference", {}, ""
                else:
                    return "no preference", {}, ""

            # - else if non-winner wins
            else:
                winner_idx = pair[1]
                if len(tpair[winner_idx]) >= 1:
                    tpair_idx = 0
                    continue
                else:  # return it
                    search_tree += ",".join(
                        [treatment_idx[pair[0]], str(treatment_predictor_sums[0]), treatment_idx[pair[1]],
                         str(treatment_predictor_sums[1])])
                    return treatment_idx[pair[1]], treatment1, search_tree

            # do mini comparison
            # get last tpair index
            last_idx = min(tpair_idx + k, len(tpair[winner_idx]) - 1)

            # convert dict predictor names to list predictor_idx
            predictor_idx = list(data['predictors']['relevance'])

            # do a tallying over a fixed set of m predictors for the next 0 to k treatments
            for i in range(tpair_idx, last_idx, 1):
                tallying_pair = tpair[winner_idx][i]
                treatment1 = data['treatment'][treatment_idx[tallying_pair[1]]]
                treatment_predictor_sums[0] = treatment_predictor_sums[1] = 0

                for predictor in predictor_idx[:m]:
                    predictor_val = data['predictors']['relevance'][predictor]

                    compare_result = self.compare_treatment_pair(predictor, predictor_val, data['casualty']['injury']['system'], treatment0, treatment1)
                    treatment_predictor_sums[0] += 1 if compare_result[0] else 0
                    treatment_predictor_sums[1] += 1 if compare_result[1] else 0

                # - if winner wins and all up to k comparisons have been made, return it
                if treatment_predictor_sums[0] > treatment_predictor_sums[1] and i == (last_idx - 1):
                    search_tree += ",".join(
                        [treatment_idx[pair[0]], str(treatment_predictor_sums[0]), treatment_idx[pair[1]],
                         str(treatment_predictor_sums[1])])
                    return treatment_idx[pair[0]], treatment0, search_tree

                # - else if comparison element wins
                if treatment_predictor_sums[0] <= treatment_predictor_sums[1]:
                    tpair_idx = i
                    break

        # if outside of while loop no definitive winner was reached
        return "no preference", {}, ""

    '''Returns the highest priority casualty according to cues used by one-bounce

    input:
    - dictionary of casualties

    output:
    - casualty id as string
    '''
    def one_bounce_priority(self, casualty_dict: dict) -> dict:

        if type(casualty_dict) != dict: raise AttributeError("Incorrect arg types or size")
        if len(casualty_dict) == 0: raise Exception("no casualties exist")

        # create table of casualty fields to worth
        casualty_val_table = dict()
        casualty_val_table['relationship'] = {'same-unit': 1, 'friend': 2}
        casualty_val_table['rank'] = {'civilian': 0, 'marine': 1, 'intel officer': 2, 'vip': 3}

        # get random ordering of casualties
        casualty_list = list(casualty_dict)
        random_idx = random.sample(range(0, len(casualty_list)), len(casualty_list))

        # compare 1st and 2nd casualty, field for field
        if len(random_idx) == 1:
            return {casualty_list[0]: casualty_dict[casualty_list[0]]}
        else:
            for i in range(len(random_idx) - 1):

                casualty0_sum = 0
                casualty1_sum = 0
                person0 = casualty_list[random_idx[i]]
                person1 = casualty_list[random_idx[i + 1]]
                info0 = casualty_dict[person0]
                info1 = casualty_dict[person1]

                casualty0_sum += 0 if info0['demographics']['rank'] is None else casualty_val_table['rank'][
                    info0['demographics']['rank'].lower()]
                casualty1_sum += 0 if info1['demographics']['rank'] is None else casualty_val_table['rank'][
                    info1['demographics']['rank'].lower()]
                casualty0_sum += 0 if info0['relationship'] == 'NONE' else casualty_val_table['relationship'][
                    info0['relationship'].lower()]
                casualty1_sum += 0 if info1['relationship'] == 'NONE' else casualty_val_table['relationship'][
                    info1['relationship'].lower()]
                casualty0_sum += 0 if info0['demographics']['age'] is None else (
                    1 if (0 <= info0['demographics']['age'] <= 10 or 65 <= info0['demographics']['age'] <= 100) else 0)
                casualty1_sum += 0 if info1['demographics']['age'] is None else (
                    1 if (0 <= info1['demographics']['age'] <= 10 or 65 <= info1['demographics']['age'] <= 100) else 0)

                for injury in info0['injuries']:
                    if isinstance(injury['severity'], float):
                        if 0.5 <= injury['severity'] <= 1: casualty0_sum += 1
                for injury in info1['injuries']:
                    if isinstance(injury['severity'], float):
                        if 0.5 <= injury['severity'] <= 1: casualty1_sum += 1

                if casualty0_sum > casualty1_sum:
                    return {person0: info0}
                elif i == len(random_idx) - 2:
                    return {person1: info1}

        # if no casualty that satisfies requirements return first in list
        return {list(casualty_dict.keys())[0]: list(casualty_dict.values())[0]}

    '''map between kdmas and treatment predictors (for future work may include casualty and scenario predictors)
    '''
    # TODO: for now convert functions are stubs, they will be flushed out later
    def convert_kdma_predictor(self, mission, denial, predictor):
        if not isinstance(mission, numbers.Number) and (0 <= mission <= 10): raise AttributeError("Incorrect arg types or size")
        if not isinstance(denial, numbers.Number) and (0 <= denial <= 10): raise AttributeError("Incorrect arg types or size")
        if type(predictor) != str: raise AttributeError("Incorrect arg types or size")

        if predictor == 'risk_reward_ratio': return 'low'
        elif predictor == 'resources': return 'few'
        elif predictor == 'time': return 'minutes'
        elif predictor == 'system': return 'equal'
        else: raise Exception("not a valid predictor")

    def convert_between_kdma_risk_reward_ratio(self, mission, denial, predictor):
        return "low"

    def convert_between_kdma_resources(self, mission, denial, predictor):
        return "few"

    def convert_between_kdma_time(self, mission, denial, predictor):
        return "minutes"

    def convert_between_kdma_system(self, mission, denial, predictor):
        return "equal"

    def convert_between_kdma_life_impact(self, mission, denial, predictor):
        return "medium"

    ''' placeholder data needed by hra strategies until functionality is implemented. Currently creates a scenario file
        with kdma associated predictor values (should be learned), predictor values for possible decisions (will be educated guess), kdma values (should be learned)
    '''
    def preprocess(self, decision_list:list) -> str:

        if type(decision_list) != list: raise AttributeError("Incorrect arg types or size")

        file = dict()

        # file["scenario"] = {"danger":"high", "urgency":"high", "error_prone":"high"}

        file["kdma"] = {"mission": 8, "denial": 3}

        # file["predictors"] = {"relevance":{"risk_reward_ratio":"low", "time":"seconds", "system":"equal", "resources":"few"}},

        temp_file = dict()
        temp_file["treatment"] = {
            "APPLY_TREATMENT": {
                "hemostatic gauze": {"risk_reward_ratio": "low", "resources": "few", "time": "seconds",
                                     "system": "cardiovascular", "life_impact": "low"},
                "tourniquet": {"risk_reward_ratio": "low", "resources": "few", "time": "minutes",
                               "system": "cardiovascular", "life_impact": "medium"},
                "pressure bandage": {"risk_reward_ratio": "low", "resources": "few", "time": "minutes", "system": "integumentary", "life_impact": "low"},
                "decompression needle": {"risk_reward_ratio": "medium", "resources": "few", "time": "minutes",
                                         "system": "respiratory", "life_impact": "low"},
                "nasopharyngeal airway": {"risk_reward_ratio": "low", "resources": "few", "time": "seconds",
                                          "system": "respiratory", "life_impact": "medium"}},
            "CHECK_ALL_VITALS": {
                "CHECK_ALL_VITALS": {"risk_reward_ratio": "low", "resources": "few", "time": "minutes",
                                     "system": "all", "life_impact": "low"}},
            "CHECK_PULSE": {
                "CHECK_PULSE": {"risk_reward_ratio": "low", "resources": "few", "time": "minutes",
                                "system": "cardiovascular", "life_impact": "low"}},
            "CHECK_RESPIRATION": {
                "CHECK_RESPIRATION": {"risk_reward_ratio": "low", "resources": "some", "time": "seconds",
                                      "system": "respiratory"}},
            "DIRECT_MOBILE_CASUALTY": {
                "DIRECT_MOBILE_CASUALTY": {"risk_reward_ratio": "medium", "resources": "few", "time": "minutes",
                                           "system": "none", "life_impact": "medium"}},
            "MOVE_TO_EVAC": {
                "MOVE_TO_EVAC": {"risk_reward_ratio": "high", "resources": "few", "time": "minutes", "system": "none", "life_impact": "high"}},
            "TAG_CASUALTY": {
                "TAG_CASUALTY": {"risk_reward_ratio": "low", "resources": "few", "time": "minutes", "system": "none", "life_impact": "high"}},
            "SITREP": {
                "SITREP": {"risk_reward_ratio": "low", "resources": "some", "time": "minutes", "system": "all", "life_impact": "low"}},
        }
        file['treatment'] = {}
        file['treatment']["APPLY_TREATMENT"] = dict()
        for decision_complete in decision_list:
            decision = decision_complete.value.name
            if decision == 'END_SCENARIO': continue
            elif decision == "APPLY_TREATMENT":
                for ele in temp_file['treatment']['APPLY_TREATMENT']:
                    if ele in file['treatment']["APPLY_TREATMENT"]: continue
                    elif ele in str(decision_complete.value).lower():
                        file['treatment']["APPLY_TREATMENT"][ele] = temp_file['treatment']['APPLY_TREATMENT'][ele]
                        break
            else:
                if decision in file['treatment']: continue
                file['treatment'][decision] = temp_file['treatment'][decision]

        file['injury_list'] = ["Forehead Scrape", "Ear Bleed", "Asthmatic", "Laceration", "Puncture", "Shrapnel",
                               "Chest Collapse", "Amputation", "Burn"]

        json_object = json.dumps(file, indent=2)
        new_file = "temp/newfile.json"
        with open(new_file, "w") as outfile:
            outfile.write(json_object)

        return new_file

    ''' determines the system likely to be impacted by the injury, and by extension the important treatment
    '''
    def guess_injury_body_system(self, location: str, injury: str) -> str:

        if type(location) != str or type(injury) != str: raise AttributeError("Incorrect arg types or size")

        if location.lower() == "unspecified" or any(ele in injury for ele in ['amputation']):
            return 'cardiovascular'
        elif any(ele in location.lower() for ele in ['calf', 'thigh', 'bicep', 'shoulder', 'forearm', 'wrist']) or\
                any(ele in injury.lower() for ele in ['forehead scrape', 'laceration', 'puncture', 'shrapnel', 'burn']):
            return 'integumentary'
        elif any(ele in location.lower() for ele in ['head', 'face', 'neck']) or any(ele in injury.lower() for ele in ['ear bleed']):
            return 'neural'
        elif any(ele in location.lower() for ele in ['chest']) or any(ele in injury.lower() for ele in ['asthmatic', 'chest collapse']):
            return 'respiratory'
        elif any(ele in location.lower() for ele in ['stomach']):
            return 'gastrointestinal'
        else: return 'unknown'

    '''
    Call each HRA strategy with scenario info and return a dict of dictionaries, each dictionary 
    corresponds to a possible decision where keys are hra strategies and values are 1 if a 
    strategy returned the decision and 0 otherwise.

    input:
    - file_name: json file that describes scenario, kdmas, casualty, predictors, and treatment info
    - data: a dictionary with the same info as file_name that may used instead of file_name
    - m, where 0 < m <= M, is the size of the set of predictors to consider when comparing 2 treatments
    - k, where 0 < k <= K, perform tallying on present winner with up to k other treatments

    output:
    - dict of dicts, where each key-value pair is the hra strategy and l if the strategy returned the decision or 0 otherwise
    - tree of search path (not implemented)
    '''
    def hra_decision_analytics(self, file_name: str, m: int = 2, k: int = 2, search_path = False, rand_seed=0, data: dict = None) -> dict:

        if (type(file_name) != str or len(file_name) == 0) and (type(data) != dict or data is None): raise AttributeError("No info to process")
        if not(isinstance(m, numbers.Number) or isinstance(k, numbers.Number)): raise AttributeError("Bad value for k or m")

        # extract possible treatments from scenario input file
        if data is None:
            with open(file_name, 'r+') as f:
                data = json.load(f)

                # extract kdma values from scenario input file
                mission = data['kdma']['mission']
                denial = data['kdma']['denial']

                for predictor in data['predictors']['relevance']:
                    data['predictors']['relevance'][predictor] = self.convert_kdma_predictor(mission, denial, predictor)

                # add predictors to scenario file
                json_object = json.dumps(data, indent=2)
                new_file = "temp/scene.json"
                with open(new_file, "w") as outfile:
                    outfile.write(json_object)

        new_file = ''
        treatment_idx = list(data['treatment'])

        # update input arg to hold the search path of each strategy
        search_tree = {'take-the-best': '', 'exhaustive': '', 'tallying': '', 'satisfactory': '', 'one-bounce': ''}

        # create a dict for each treatment to hold corresponding HRA strategies
        decision_hra = dict()
        for treatment in treatment_idx:
            decision_hra[treatment] = {'take-the-best': 0, 'exhaustive': 0, 'tallying': 0, 'satisfactory': 0,
                                       'one-bounce': 0}
        decision_hra["no preference"] = {'take-the-best': 0, 'exhaustive': 0, 'tallying': 0, 'satisfactory': 0,
                                         'one-bounce': 0}

        # call each HRA strategy and store the result with the matching decision list
        take_the_best_result = self.take_the_best(new_file, search_path=search_path, data=data)
        decision_hra[take_the_best_result[0]]['take-the-best'] += 1

        exhaustive_result = self.exhaustive(new_file, search_path=search_path, data=data)
        decision_hra[exhaustive_result[0]]['exhaustive'] += 1

        tallying_result = self.tallying(new_file, m, search_path=search_path, data=data,
                                            seed=rand_seed)
        decision_hra[tallying_result[0]]['tallying'] += 1

        satisfactory_result = self.satisfactory(new_file, m, seed=rand_seed, data=data)
        decision_hra[satisfactory_result[0]]['satisfactory'] += 1

        one_bounce_result = self.one_bounce(new_file, m, k, search_path=search_path, data=data)
        decision_hra[one_bounce_result[0]]['one-bounce'] += 1

        search_tree['take-the-best'] = take_the_best_result[2]
        search_tree['exhaustive'] = exhaustive_result[2]
        search_tree['tallying'] = tallying_result[2]
        search_tree['satisfactory'] = satisfactory_result[2]
        search_tree['one-bounce'] = one_bounce_result[2]

        # return all hra decision analysis elements
        return {
            "decision_hra_dict": decision_hra,
            #"learned_kdma_set": {'mission': mission, 'denial': denial},
            #"learned_predictors": predictors,
            #"decision_comparison_order": search_tree
        }

    '''Parent class function that calls hra_decision_analytics
    '''

    # TODO: refactor and test
    def analyze(self, scen: Scenario, probe) -> dict[str, DecisionMetrics]:

        # create scenario file
        new_file = self.preprocess(probe.decisions)
        with open(new_file, 'r+') as f:
            data = json.load(f)

        casualty_data = dict()
        for ele in scen.state.casualties:
            casualty_data[ele.id] = {
                "id": ele.id,
                "name": ele.name,
                "injuries":[{"location":l.location,"name":l.name,"severity":l.severity} for l in ele.injuries],
                "demographics": {"age": ele.demographics.age, "sex": ele.demographics.sex,
                                 "rank": ele.demographics.rank},
                "vitals": {"breathing": ele.vitals.breathing, "hrpmin": ele.vitals.hrpmin,
                           "conscious": ele.vitals.conscious, "mental_status": ele.vitals.mental_status},
                "tag": ele.tag, "assessed": ele.assessed, "relationship": ele.relationship
            }
        # get priority for each hra strategy
        priority_take_the_best = self.take_the_best_priority(casualty_data, data['kdma'])
        priority_exhaustive = self.exhaustive_priority(casualty_data)
        priority_tallying = self.tallying_priority(casualty_data)
        priority_satisfactory = self.satisfactory_priority(casualty_data)
        priority_one_bounce = self.one_bounce_priority(casualty_data)

        #  for each casualty and each predictor set combination get the hra analytics
        temp_data = copy.deepcopy(data)
        ensemble_set = {}
        all_predictors = {'time': 'seconds', 'resources': 'few', 'risk_reward_ratio': 'low', 'system': 'equal'} # TODO calculate predictors based on kdmas
        for n in range(2, len(all_predictors) + 1):
            set_sz = n

            predictor_combos = self.gen_predictor_combo(all_predictors, set_sz)  # run hra for each of the possible combinations of predictors
            casualty_analytics = []

            for casualty in casualty_data:
                injury_cnt = min(1, len(casualty_data[casualty]['injuries']))
                injury_cnt = range(injury_cnt)
                casualty_data[casualty]['injury'] = {'system':"None"}
                for i in injury_cnt:
                    casualty_data[casualty]['injury']['system'] = self.guess_injury_body_system(casualty_data[casualty]['injuries'][i]['location'], casualty_data[casualty]['injuries'][i]['name'])
                temp_data['casualty'] = casualty_data[casualty]
                temp_data['treatment'] = {}

                result = {}
                for pred in predictor_combos:
                    temp_data['predictors'] = {'relevance': pred}
                    for treatment in data['treatment']:
                        rel_treatment_found = [x for x in probe.decisions if x.value.name == treatment and x.value.params['casualty'] == casualty]
                        if len(rel_treatment_found):
                            for name, val in data['treatment'][treatment].items():
                                temp_data['treatment'][name] = {}
                                for vpred in val:
                                    if vpred in pred:
                                        temp_data['treatment'][name][vpred] = val[vpred]
                    hash_ele = '-'.join(x for x in pred)
                    m_arg = int(set_sz * 0.8) # number of predictors to start with before increasing for tallying, one-bounce, and satisfactory
                    result[hash_ele] = self.hra_decision_analytics(new_file, data=temp_data, m=m_arg)
                casualty_analytics.append({casualty: result})

            ensemble_set[n] = copy.deepcopy(casualty_analytics)

        # extract casualty analytics of all predictor combinations from ensemble_set
        casualty_analytics = []
        for key in casualty_data.keys():
            casualty_val = {}
            for ensemble_key, ensemble_val in ensemble_set.items():
                for s in range(len(ensemble_val)):
                    if list(ensemble_val[s].keys())[0] == key:
                        for combo_key, combo_val in ensemble_val[s].items():
                            for ele_key, ele_val in combo_val.items():
                                casualty_val[ele_key] = ele_val
            combo_result = {copy.deepcopy(key):copy.deepcopy(casualty_val)}
            casualty_analytics.append(copy.deepcopy(combo_result))

        # package decision metrics by decision
        analysis = {}
        for decision_complete in probe.decisions:
            decision = decision_complete.value.name
            if decision == "APPLY_TREATMENT":
                for ele in data['treatment']['APPLY_TREATMENT']:
                    if ele in str(decision_complete.value).lower():
                        decision = ele
                        break
            hra_strategy = {}
            for ele in casualty_analytics:
                ele_key = list(ele.keys())[0]
                ele_val = list(ele.values())[0]
                if not(ele_key in str(decision_complete.value)): continue

                ele_key = str(decision_complete.value)
                hra_strategy[ele_key] = {vp: {'take-the-best': 0, 'exhaustive': 0, 'tallying': 0, 'satisfactory': 0,
                                    'one-bounce': 0} for vp in ele_val}
                for val_predictor in ele_val:

                    hra_strategy[ele_key][val_predictor]['take-the-best'] = ele_val[val_predictor]['decision_hra_dict'][decision]['take-the-best']
                    hra_strategy[ele_key][val_predictor]['exhaustive'] = ele_val[val_predictor]['decision_hra_dict'][decision]['exhaustive']
                    hra_strategy[ele_key][val_predictor]['tallying'] = ele_val[val_predictor]['decision_hra_dict'][decision]['tallying']
                    hra_strategy[ele_key][val_predictor]['satisfactory'] = ele_val[val_predictor]['decision_hra_dict'][decision]['satisfactory']
                    hra_strategy[ele_key][val_predictor]['one-bounce'] = ele_val[val_predictor]['decision_hra_dict'][decision]['one-bounce']

            match len(hra_strategy.values()):
                case 0:
                    #No result
                    ret = {}
                case 1:
                    #standard?
                    ret = list(hra_strategy.values())[0]
                case _:
                    # How?
                    breakpoint()
                    raise Exception()
            
            metrics: DecisionMetrics = {
                "All Predictors": DecisionMetric(name="All Predictors", description="Full set of predictors with kdma associated values", value={'-'.join(key + '(' + str(val) + ')' for key, val in data['kdma'].items()):all_predictors}),\
                "HRA Strategy": DecisionMetric(name="HRA Strategy", description="Applicable hra strategies", value=ret),\
                "Take-The-Best Priority": DecisionMetric(name="Take-The-Best Priority",
                                                         description="Priority for take-the-best strategy",
                                                         value=str(list(priority_take_the_best.keys())[0]) in str(decision_complete.value)), \
                "Exhaustive Priority": DecisionMetric(name="Exhaustive Priority",
                                                      description="Priority for exhaustive strategy",
                                                      value=str(list(priority_exhaustive.keys())[0]) in str(decision_complete.value)), \
                "Tallying Priority": DecisionMetric(name="Tallying Priority",
                                                    description="Priority for tallying strategy",
                                                    value=str(list(priority_tallying.keys())[0]) in str(decision_complete.value)), \
                "Satisfactory Priority": DecisionMetric(name="Satisfactory Priority",
                                                        description="Priority for satisfactory strategy",
                                                        value=str(list(priority_satisfactory.keys())[0]) in str(decision_complete.value)), \
                "One-Bounce Priority": DecisionMetric(name="One-Bounce Priority",
                                                      description="Priority for one-bounce strategy",
                                                      value=str(list(priority_one_bounce.keys())[0]) in str(decision_complete.value))
                }
            # Update the metrics in the decision with our currently calculated metrics
            decision_complete.metrics.update(metrics)
            analysis[decision_complete.id_] = metrics
        return analysis