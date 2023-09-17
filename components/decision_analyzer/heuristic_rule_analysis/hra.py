import json
import random
import copy
from pathlib import Path
from domain.internal import Probe, Scenario, Decision, DecisionMetrics, DecisionMetric
from components import DecisionAnalyzer

# currently runs for set of possible decisions, future may change to be called for each decision
class HeuristicRuleAnalyzer(DecisionAnalyzer):
    STRATEGIES = ["take-the-best", "exhaustive", "tallying", "satisfactory", "one-bounce"]

    def __init__(self):
        super().__init__()

    # make all permutations of decision pairs based on their list index 
    def make_dspace_permutation_pairs(self, obj_cnt):
        dsize = int((obj_cnt) * (obj_cnt - 1) / 2)
        d = list()

        for i in range(obj_cnt):
            for j in range (i, -1, -1):
                if i != j:
                    d.append((i,j))
        
        if len(d) == dsize:
            return d
        else:
            return "error, size mismatch"

    '''
    Take-the-best: Given a set of predictors ranked by validity, and n treatments in the decision space, return the treatment that performs 
    best in terms of its predictor values matching with kdm predictor values. In the case where there are multiple highest 
    performing treatments, return "no preference". The comparisons are performed among Σ(n-1) treatment pairs, with each 
    treatment compared to every other treatment once. A comparison stops after the first predictor that discriminates.

    input: 
    - json file with scenario, predictors, casualty, and treatment info, where predictors preferences are ranked according to validity

    output:
    - decision
    '''
    def take_the_best(self, file_name:str, search_path=False)->tuple:

    # prep the input
    # - open the file
        f = open(file_name)

    # get dict from data and convert treatment dict to list
        data = json.load(f)
        treatment_idx = list(data['treatment'])

    # if there is only a single treatment in the decision space
        if len(treatment_idx) == 1:
            return (treatment_idx[0], data['treatment'][treatment_idx[0]])
        
    # if search_path then return as part of output the order of pairs and their scores
        if search_path:
            search_tree = str()

    # generate permutations of "battles" between treatments
        treatment_pairs = self.make_dspace_permutation_pairs(len(treatment_idx))

    # create container to hold number of "battles" won for each treatment
        treatment_sums = [0]*len(treatment_idx)

    # iterate through treatment pairs
        for battle in treatment_pairs:
            treatment0 = data['treatment'][treatment_idx[battle[0]]]
            treatment1 = data['treatment'][treatment_idx[battle[1]]]

    # - for each predictor, compare treatment and predictor values
            for predictor in data['predictors']['relevance']:
                predictor_val = data['predictors']['relevance'][predictor]#[0]

    # - - if a treatment wins the round add 1 to its score and end the comparison
    # - - - special case for system predictor
                if predictor == "system":
                    if (treatment0[predictor] == data['casualty']['injury']['system'] or treatment0[predictor] == "all") and\
                        not (treatment1[predictor] == data['casualty']['injury']['system'] or treatment1[predictor] == "all"):
                        treatment_sums[battle[0]] += 1
                        if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(treatment_sums[battle[0]]) + ","\
                            + str(treatment_idx[battle[1]]) + "," + str(treatment_sums[battle[1]]) + ","
                        break

                    elif (treatment1[predictor] == data['casualty']['injury']['system'] or treatment1[predictor] == "all") and\
                        not (treatment0[predictor] == data['casualty']['injury']['system'] or treatment0[predictor] == "all"):
                        treatment_sums[battle[1]] += 1
                        if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(treatment_sums[battle[0]]) + ","\
                            + str(treatment_idx[battle[1]]) + "," + str(treatment_sums[battle[1]]) + ","
                        break           
                            
    # - - - normal case for predictor
                else:
                    if treatment0[predictor] == predictor_val and not (treatment1[predictor] == predictor_val):
                        treatment_sums[battle[0]] += 1
                        if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(treatment_sums[battle[0]]) + ","\
                            + str(treatment_idx[battle[1]]) + "," + str(treatment_sums[battle[1]]) + ","
                        break
                    elif treatment1[predictor] == predictor_val and not (treatment0[predictor] == predictor_val):
                        treatment_sums[battle[1]] += 1
                        if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(treatment_sums[battle[0]]) + ","\
                            + str(treatment_idx[battle[1]]) + "," + str(treatment_sums[battle[1]]) + ","
                        break

    # close file
        f.close()

    # if there is an overall winner, return it
    # - get the max value
        max_val = max(treatment_sums)
        sequence = range(len(treatment_sums))
        list_indices = [index for index in sequence if treatment_sums[index] == max_val]

    # - if there is not tie, the treatment with the max value wins
        if len(list_indices) == 1:

    # - - return treatment, info pair corresponding to max index or "no preference"
            if search_path:
                return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]], search_tree)
            else:
                return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]])
        else:
            if search_path:
                return ("no preference", "", search_tree)
            else:
                return ("no preference", "")

    '''
    Exhaustive: Search strategy that ranks ALL decisions in decisions space according to 
    ALL relevance predictor values and returns the highest ranked treatment

    input: 
    - json file thats describes scenario, predictor, casualty, decision space

    output:
    - decision
    '''
    def exhaustive(self, file_name:str, search_path=False)->tuple:

    # prep inputs
    # - open file
        f = open(file_name)

    # get dict from data and convert treatment dict to list
        data = json.load(f)
        treatment_idx = list(data['treatment'])

    # if there is only a single treatment in the decision space
        if len(treatment_idx) == 1:
            return (treatment_idx[0], data['treatment'][treatment_idx[0]])

    # create corresponding array to hold treatment scores
        all_treatment_sum = list()
        treatment_sum = 0

    # for each treatment and sum in treatment list
        for treatment in treatment_idx:
            
    # - for each predictor in set check its value against that of the predictor
            for predictor in data['predictors']['relevance']:
                predictor_val = data['predictors']['relevance'][predictor]#[0]

    # - - if the value matches, add 1 to the treatment sum
    # - - - special case for system predictor
                if predictor == "system":
                    if data['treatment'][treatment][predictor] == data['casualty']['injury']['system'] or\
                        data['treatment'][treatment][predictor] == "all":
                        treatment_sum += 1

    # - - - normal case for predictor
                else:
                    if data['treatment'][treatment][predictor] == predictor_val:
                        treatment_sum += 1

    # - add treatment sum to list and reset     
            all_treatment_sum.append(treatment_sum)
            treatment_sum = 0

    # close file
        f.close()

    # if search_path true store search order
        if search_path:
            search_tree = ""
            for i in range(len(treatment_idx)):
                search_tree += str(treatment_idx[i]) + "," + str(all_treatment_sum[i]) + ","

    # return winner
    # - get max value(s) index from sums
        max_val = max(all_treatment_sum)
        sequence = range(len(all_treatment_sum))
        list_indices = [index for index in sequence if all_treatment_sum[index] == max_val]

    # - if the max isn't tied
        if len(list_indices) == 1:

    # - - return treatment, info pair corresponding to max index
            if search_path:
                return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]], search_tree)
            else:
                return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]])

    # - if the max is tied return "no preference"
        else:
            if search_path:
                return ("no preference", "", search_tree)
            else:
                return ("no preference", "")

    '''
    Tallying: Given a set of randomly selected predictors m, where m ⊆ M (the complete set of predictors), and n treatments 
    in the decision space, return the treatment that performs best in terms of its predictor values matching with kdm 
    predictor values. The comparisons are performed among Σ(n-1) treatment pairs, with each treatment compared to every other 
    treatment once. If one treatment performs better add 1 to its sum and continue to the next treatment pair. If two 
    treatments perform equally with respect to the set m, and |m| < |M|, randomly select one of the 
    remaining predictors from M, comparing the treament pair against this new predictor; if |m| == |M|, 
    continue to the next treatement pair. Return the treatment that performed best relative to the other treatments, or 
    "no preference" if there no clear winner.

    input: 
    - json file with scenario, predictors, casualty, and treatment info
    - m, where 0 < m <= M, is the size of the set of predictors to consider when comparing 2 treatments

    output: decision
    '''
    def tallying(self, file_name:str, m:int, seed=None, search_path=False)->tuple:

    # set random seed
        if seed != None:
            random.seed(seed)

    # prep inputs
    # - open file
        f = open(file_name)

    # - convert dictionary treatment names to list
        data = json.load(f)
        treatment_idx = list(data['treatment'])

    # if there is only a single treatment in the decision space
        if len(treatment_idx) == 1:
            return (treatment_idx[0], data['treatment'][treatment_idx[0]])
        
    # if search_path then return as part of output the order of pairs and their scores
        if search_path:
            search_tree = str()

    # select random set of m predictors
    # - convert dict predictor names to list
        predictor_idx = list(data['predictors']['relevance'])
        
    # - get m random indices for predictors
        #rand_predictor_idx = random.sample(range(0, len(predictor_idx)), m)
        rand_predictor_idx = random.sample(range(0, len(predictor_idx)), len(predictor_idx))
        
    # prepare variables for battles
    # - generate permutations of "battles" between treatments
        treatment_pairs = self.make_dspace_permutation_pairs(len(treatment_idx))

    # - create container to hold number of "battles" won for each treatment
        treatment_sums = [0]*len(treatment_idx)

    # - create container to hold number of predictors matched for each treatment
        treatment_predictor_sums = [0]*2

    # do battles between treatments
    # - iterate through treatment pairs
        for battle in treatment_pairs:
            treatment0 = data['treatment'][treatment_idx[battle[0]]]
            treatment1 = data['treatment'][treatment_idx[battle[1]]]
            treatment_predictor_sums[0] = treatment_predictor_sums[1] = 0

    # - - for each predictor, compare treatment and predictor values
            for h in rand_predictor_idx[:m]:
                predictor = predictor_idx[h]
                predictor_val = data['predictors']['relevance'][predictor]#[0]

    # - - - if there is a match between treatment and predictor values, add 1 to treatment predictor sum
    # - - - - special case for system predictor
                if predictor == "system":
                    if treatment0[predictor] == data['casualty']['injury']['system'] or treatment0[predictor] == "all":
                        treatment_predictor_sums[0] += 1

                    if treatment1[predictor] == data['casualty']['injury']['system'] or treatment1[predictor] == "all": 
                        treatment_predictor_sums[1] += 1          
                            
    # - - - - normal case for predictor
                else:
                    if treatment0[predictor] == predictor_val:
                        treatment_predictor_sums[0] += 1

                    if treatment1[predictor] == predictor_val:
                        treatment_predictor_sums[1] += 1

    # get the round winner
    # - - if the two treament scores are not equal
            if treatment_predictor_sums[0] != treatment_predictor_sums[1]:

    # - - - add one to treament score of treatment with highest sum
                treatment_sums[battle[0] if treatment_predictor_sums[0] > treatment_predictor_sums[1] else battle[1]] += 1
                
                if search_path:  search_tree += str(treatment_idx[battle[0]]) + "," + str(treatment_predictor_sums[0]) + ","\
                            + str(treatment_idx[battle[1]]) + "," + str(treatment_predictor_sums[1]) + ","
                    
    # - - else if the two treatment scores are equal
            else:
    # - - - get M\m set of random predictors
                rrand_predictor_idx =  rand_predictor_idx[m:]

    # - - - while size of set M\m is not empty
                for i in rrand_predictor_idx:
                    rpredictor = predictor_idx[i]
                    rpredictor_val = data['predictors']['relevance'][rpredictor]

    # - - - - if there is a match between treatment and predictor values, add 1 to treatment predictor sum
    # - - - - - special case for system predictor
                    if rpredictor == "system":
                        if treatment0[rpredictor] == data['casualty']['injury']['system'] or treatment0[rpredictor] == "all":
                            treatment_predictor_sums[0] += 1

                        if treatment1[rpredictor] == data['casualty']['injury']['system'] or treatment1[rpredictor] == "all":
                            treatment_predictor_sums[1] += 1           
                                
    # - - - - - normal case for predictor
                    else:
                        if treatment0[rpredictor] == rpredictor_val:
                            treatment_predictor_sums[0] += 1

                        if treatment1[rpredictor] == rpredictor_val:
                            treatment_predictor_sums[1] += 1

    # - - - - get the round winner
    # - - - - - if the two treament scores are not equal
                    if treatment_predictor_sums[0] != treatment_predictor_sums[1]:

    # - - - - - - add one to treament score of treatment with highest sum and continue to next treatment pair
                        treatment_sums[battle[0] if treatment_predictor_sums[0] > treatment_predictor_sums[1] else battle[1]] += 1
                        
                        if search_path:  search_tree += str(treatment_idx[battle[0]]) + "," + str(treatment_predictor_sums[0]) + ","\
                            + str(treatment_idx[battle[1]]) + "," + str(treatment_predictor_sums[1]) + ","

                        break

    # close file
        f.close()

    # return a decision
    # - get the max value
        max_val = max(treatment_sums)
        sequence = range(len(treatment_sums))
        list_indices = [index for index in sequence if treatment_sums[index] == max_val]

    # - if there is not tie, the treatment with the max value wins
        if len(list_indices) == 1:

    # - - return treatment, info pair corresponding to max index or "no preference"
            if search_path:
                return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]], search_tree)
            else:
                return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]])
        else:
            if search_path:
                return ("no preference", "", search_tree)
            else:
                return ("no preference", "")

    '''
    Satisfactory: Given a set of randomly selected predictors m, where m ⊆ M (the complete set of predictors),
    and n treatments in the decision space, return the treatment that performs best in terms of its predictor values
    matching with kdma associated predictor values. The comparisons are performed among Σ(n-1) treatment pairs,
    with each treatment compared to every other treatment once. A comparison stops after the first predictor that discriminates.
    If two treatments perform equally with respect to the set m, and the size of m < the size of M, randomly select one of the
    remaining predictors from M comparing the treament pair against this new predictor; if the size of m equals that of M,
    continue to the next treatement pair. Return the treatment that performed best relative to the other treatments, or
    "no preference" if there no clear winner.
    '''
    def satisfactory(self, file_name:str, m:int, seed=None, search_path=False)->tuple:

    # set random seed
        if seed != None:
            random.seed(seed)

    # prep inputs
    # - open file
        f = open(file_name)

    # - convert dictionary treatment names to list
        data = json.load(f)
        treatment_idx = list(data['treatment'])

    # if there is only a single treatment in the decision space
        if len(treatment_idx) == 1:
            return (treatment_idx[0], data['treatment'][treatment_idx[0]])
        
    # if search_path then return as part of output the order of pairs and their scores
        if search_path:
            search_tree = str()

    # track if a round had a winner over m predictors
        winner = False

    # select random set of m predictors
    # - convert dict predictor names to list
        predictor_idx = list(data['predictors']['relevance'])
        
    # - get m random indices for predictors
        rand_predictor_idx = random.sample(range(0, len(predictor_idx)), len(predictor_idx))
        
    # prepare variables for battles
    # - generate permutations of "battles" between treatments
        treatment_pairs = self.make_dspace_permutation_pairs(len(treatment_idx))

    # - create container to hold number of "battles" won for each treatment
        treatment_sums = [0]*len(treatment_idx)

    # do battles between treatments
    # - iterate through treatment pairs
        for battle in treatment_pairs:
            treatment0 = data['treatment'][treatment_idx[battle[0]]]
            treatment1 = data['treatment'][treatment_idx[battle[1]]]
            winner = False

    # - - for each predictor, compare treatment and predictor values
            for h in rand_predictor_idx[:m]:
                predictor = predictor_idx[h]
                predictor_val = data['predictors']['relevance'][predictor]#[0]

    # - - - if a treatment wins the round add 1 to its score and end the comparison
    # - - - - special case for system predictor
                if predictor == "system":
                    if (treatment0[predictor] == data['casualty']['injury']['system'] or treatment0[predictor] == "all") and\
                        not (treatment1[predictor] == data['casualty']['injury']['system'] or treatment1[predictor] == "all"):
                        treatment_sums[battle[0]] += 1
                        winner = True
                        if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(1) + ","\
                            + str(treatment_idx[battle[1]]) + "," + str(0) + ","  # NOTE: double check this in debug mode, only counts when there is a difference, not total sum, tallying has original code
                        break

                    elif (treatment1[predictor] == data['casualty']['injury']['system'] or treatment1[predictor] == "all") and\
                        not (treatment0[predictor] == data['casualty']['injury']['system'] or treatment0[predictor] == "all"):
                        treatment_sums[battle[1]] += 1
                        winner = True
                        if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(0) + ","\
                            + str(treatment_idx[battle[1]]) + "," + str(1) + ","   # NOTE: double check this in debug mode, only counts when there is a difference, not total sum, tallying has original code
                        break           
                            
    # - - - - normal case for predictor
                else:
                    if treatment0[predictor] == predictor_val and not (treatment1[predictor] == predictor_val):
                        treatment_sums[battle[0]] += 1
                        winner = True
                        if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(1) + ","\
                            + str(treatment_idx[battle[1]]) + "," + str(0) + "," # NOTE: check special case comment
                        break
                    elif treatment1[predictor] == predictor_val and not (treatment0[predictor] == predictor_val):
                        treatment_sums[battle[1]] += 1
                        winner = True
                        if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(0) + ","\
                            + str(treatment_idx[battle[1]]) + "," + str(1) + "," # NOTE: check special case comment
                        break
    # get the round winner
    # - - if the two treament scores are not equal
            if winner: continue
                
    # - - else if the two treatment scores are equal
            else:
    # - - - get M\m set of random predictors
                rrand_predictor_idx = rand_predictor_idx[m:]

    # - - - while size of set M\m is not empty
                for i in rrand_predictor_idx:
                    rpredictor = predictor_idx[i]
                    rpredictor_val = data['predictors']['relevance'][rpredictor]

    # - - - - if there is a match between treatment and predictor values, add 1 to treatment predictor sum
    # - - - - - special case for system predictor
                    if rpredictor == "system":

                        if (treatment0[rpredictor] == data['casualty']['injury']['system'] or treatment0[rpredictor] == "all") and\
                            not (treatment1[rpredictor] == data['casualty']['injury']['system'] or treatment1[rpredictor] == "all"):
                            treatment_sums[battle[0]] += 1
                            #winner = True
                            if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(1) + ","\
                                + str(treatment_idx[battle[1]]) + "," + str(0) + ","  # NOTE: double check this in debug mode, only counts when there is a difference, not total sum, tallying has original code
                            break

                        elif (treatment1[rpredictor] == data['casualty']['injury']['system'] or treatment1[rpredictor] == "all") and\
                            not (treatment0[rpredictor] == data['casualty']['injury']['system'] or treatment0[rpredictor] == "all"):
                            treatment_sums[battle[1]] += 1
                            #winner = True
                            if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(0) + ","\
                                + str(treatment_idx[battle[1]]) + "," + str(1) + ","   # NOTE: double check this in debug mode, only counts when there is a difference, not total sum, tallying has original code
                            break           
        
    # - - - - - normal case for rpredictor
                    else:

                        if treatment0[rpredictor] == rpredictor_val and not (treatment1[rpredictor] == rpredictor_val):
                            treatment_sums[battle[0]] += 1
                            #winner = True
                            if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(1) + ","\
                                + str(treatment_idx[battle[1]]) + "," + str(0) + "," # NOTE: check special case comment
                            break
                        elif treatment1[rpredictor] == rpredictor_val and not (treatment0[rpredictor] == rpredictor_val):
                            treatment_sums[battle[1]] += 1
                            #winner = True
                            if search_path: search_tree += str(treatment_idx[battle[0]]) + "," + str(0) + ","\
                                + str(treatment_idx[battle[1]]) + "," + str(1) + "," # NOTE: check special case comment
                            break

    # close file
        f.close()

    # return a decision
    # - get the max value
        max_val = max(treatment_sums)
        sequence = range(len(treatment_sums))
        list_indices = [index for index in sequence if treatment_sums[index] == max_val]

    # - if there is not tie, the treatment with the max value wins
        if len(list_indices) == 1:

    # - - return treatment, info pair corresponding to max index or "no preference"
            if search_path:
                return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]], search_tree)
            else:
                return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]])
        else:
            if search_path:
                return ("no preference", "", search_tree)
            else:
                return ("no preference", "")

    '''
    One-Bounce: If there is a randomly ordered sequence of decisions, when two decisions are compared against all predictors,
    if the heuristic (partial calculation with tallying over fixed, ranked, deterministic set m) indicates that the winner will not change in the next
    (0 to k) comparisons where k ⊆ of K (the complete set of possible treatments), stop and take the winner. Otherwise,
    immediately stop the 0 to k comparisons and repeat the process with a comparison on M predictors between the current winner and
    the new potential winner, again checking (0 to k) treatments ahead. The comparisons are performed among Σ(n-1) treatment pairs,
    with each treatment compared to every other treatment at most twice (once with m predictors, and again with M predictors).
    If no treatment is returned via the above process return "no preference".

    input:
    - json file with scenario, kdma, casualty, RANKED predictors, and treatment info
    - m, where 0 < m <= M predictors to consider when comparing 2 treatments
    - k, where 0 < k <= K, perform tallying on present winner with up to k other treatments

    output: decision
    '''
    def one_bounce(self, file_name:str, m:int, k:int, search_path=False)->tuple:

    # prep the input
    # - open the file, get dict from data, and convert treatment dict to list
        with open(file_name, 'r') as f:
            data = json.load(f)
        treatment_idx = list(data['treatment'])

    # if there is only a single treatment in the decision space
        if len(treatment_idx) == 1:
            return (treatment_idx[0], data['treatment'][treatment_idx[0]]) #NOTE: update to reflect more complex return type
        
    # if search_path then return as part of output the order of pairs and their scores
        if search_path:
            search_tree = str()

    # generate permutations of "battles" between treatments
        treatment_pairs = self.make_dspace_permutation_pairs(len(treatment_idx))#self.make_dspace_permutation_pairs(len(treatment_idx))

    # create container to hold number of "battles" won for each treatment
        treatment_sums = [0]*len(treatment_idx) # NOTE: do we need this? think not

    # create container to hold number of predictors matched for each treatment
        treatment_predictor_sums = [0]*2

    # store "battles" in list e.g. list[list] -> battle[0] = [1, 2, 3, 4], battle[1] = [2, 3, 4]
        battle = [None]*len(treatment_idx)
        #for l in range(len(treatment_pairs) - 1, -1, -1):
        for  ele in treatment_pairs:
        #    ele = treatment_pairs[l]
            first = ele[1]
            #second = ele[1]
            if battle[first] == None:#len(battle) - 1 < first:#len(battle[first]) == 0:
                #battle.append(list())
                battle[first] = list()
                battle[first].append((ele[1], ele[0]))#[second]
            else:
                battle[first].append((ele[1], ele[0]))#(second)
        battle[-1] = list()

    # loop through battle pairs
        cnt = len(treatment_pairs)
        winner_idx = None
        battle_idx = None
        if len(battle) >= 1:
            if len(battle[0]) >=1:
                winner_idx = 0
                battle_idx = 0
        else:
            return "no battles"

    # continue checking battles, while number of battle < num of battle pairs
        while(cnt > 0):
            cnt -= 1
    # - do main battle
    # - - get treatment pairs
            pair = battle[winner_idx][battle_idx]
            treatment0 = data['treatment'][treatment_idx[pair[0]]]
            treatment1 = data['treatment'][treatment_idx[pair[1]]]
            treatment_predictor_sums[0] = treatment_predictor_sums[1] = 0

    # - - iterate through each of M predictors
            for predictor in data['predictors']['relevance']:
                predictor_val = data['predictors']['relevance'][predictor]

    # - - - if there is a match between treatment and predictor values, add 1 to treatment predictor sum
    # - - - - special case for system predictor
                if predictor == "system":
                    if treatment0[predictor] == data['casualty']['injury']['system'] or treatment0[predictor] == "all":
                        treatment_predictor_sums[0] += 1

                    if treatment1[predictor] == data['casualty']['injury']['system'] or treatment1[predictor] == "all": 
                        treatment_predictor_sums[1] += 1          
                            
    # - - - - normal case for predictor
                else:
                    if treatment0[predictor] == predictor_val:
                        treatment_predictor_sums[0] += 1

                    if treatment1[predictor] == predictor_val:
                        treatment_predictor_sums[1] += 1

    # get the round winner
    # - if winner wins
            if treatment_predictor_sums[0] > treatment_predictor_sums[1]:
    # - - if winner has no more battle pairs
                if battle_idx >= len(battle[winner_idx]) - 1:
                    if search_path: 
                        search_tree += str(treatment_idx[pair[0]]) + "," + str(treatment_predictor_sums[0]) + ","\
                                + str(treatment_idx[pair[1]]) + "," + str(treatment_predictor_sums[1]) + ","
                        return (treatment_idx[pair[0]], treatment0, search_tree)
                    else:
                        return (treatment_idx[pair[0]], treatment0)
    # - - if winner has more battle pairs
                elif battle_idx < len(battle[winner_idx]) - 1: # got some stuff to do
                    battle_idx += 1

    # - if winner and fighter are equal continue to next set of pairs
            elif treatment_predictor_sums[0] == treatment_predictor_sums[1]:
                if winner_idx < len(battle) - 1: #NOTE: find better future solution, although they tie, they could have the highest predictors sums of all pairs
                    winner_idx +=  1
                    if len(battle[winner_idx]) >= 1:
                        battle_idx = 0
                        continue
                    else:
                        return ("no preference", "")
                else:
                    return ("no preference", "") # NOTE: should sequence tree be returned?

    # - else if fighter wins
            else:
                winner_idx = pair[1]
                if len(battle[winner_idx]) >= 1:
                    battle_idx = 0
                    treatment0 = copy.deepcopy(treatment1)
                    continue
                else: # return it
                    if search_path: 
                        search_tree += str(treatment_idx[pair[0]]) + "," + str(treatment_predictor_sums[0]) + ","\
                                + str(treatment_idx[pair[1]]) + "," + str(treatment_predictor_sums[1]) + ","
                        return (treatment_idx[pair[1]], treatment1, search_tree)
                    else:
                        return (treatment_idx[pair[1]], treatment0)

    # do mini battle
    # get last battle index 
            last_idx = min(battle_idx + k - 1, len(battle[winner_idx]) - 1)
    # convert dict predictor names to list predictor_idx
            predictor_idx = list(data['predictors']['relevance'])
    # set a new winner bool and next treatment
            #new_winner = False

    # do a tallying over a fixed set of m predictor for the next 0 to k treatments
            for i in range(battle_idx, last_idx, 1):
                treatment1 = data['treatment'][treatment_idx[i]]
                treatment_predictor_sums[0] = treatment_predictor_sums[1] = 0

                for predictor in predictor_idx[:m]:
                #for j in predictor_idx[:m]:
                    #predictor = predictor_idx[j]
                    predictor_val = data['predictors']['relevance'][predictor]

    # - - - if there is a match between treatment and predictor values, add 1 to treatment predictor sum
    # - - - - special case for system predictor
                    if predictor == "system":
                        if treatment0[predictor] == data['casualty']['injury']['system'] or treatment0[predictor] == "all":
                            treatment_predictor_sums[0] += 1

                        if treatment1[predictor] == data['casualty']['injury']['system'] or treatment1[predictor] == "all": 
                            treatment_predictor_sums[1] += 1          
                                
    # - - - - normal case for predictor
                    else:
                        if treatment0[predictor] == predictor_val:
                            treatment_predictor_sums[0] += 1

                        if treatment1[predictor] == predictor_val:
                            treatment_predictor_sums[1] += 1

    # - if winner wins and all up to k comparisons have been made, return it
                if treatment_predictor_sums[0] > treatment_predictor_sums[1] and i == last_idx:
                    if search_path: 
                        search_tree += str(treatment_idx[pair[0]]) + "," + str(treatment_predictor_sums[0]) + ","\
                                + str(treatment_idx[pair[1]]) + "," + str(treatment_predictor_sums[1]) + ","
                        return (treatment_idx[pair[0]], treatment0, search_tree)
                    else:
                        return (treatment_idx[pair[0]], treatment0)
    # - else if fighter wins
                if treatment_predictor_sums[0] <= treatment_predictor_sums[1]:
                    #new_winner = True
                    battle_idx = i
                    break

    # if there is a new winner return to main battle
            #if new_winner:
    # - - break

    # if outside of while loop no definitive winner was reahed
        return ("no preference", "")

    '''
    Select the next casualty to treat, using the kdma mission. If the value is high, then VIPs are the priority.
    If the value is low, civilians are the priority. Casualty filed considered are rank, hrpmin, spo2,and rr

    input:
    - a list of casulties with values for each casualties in the fields: age, sex, rank, hrpmin, mmhg, spo2, rr, pain

    output:
    - the next casualty to treat from the list of casualties, as a dicitionary entry with casulaty id as key
    and remaining fields as the value
    '''
    def choose_next_casualty(self, casualty_list:dict, kdma_list:dict, injury_list:list)->dict:

    # store casualty
        next_casualty = dict()
        
        next_casualty_id = []
        if len(next_casualty_id) == 0:
            next_casualty_id = [key for key, value in casualty_list.items() if value['relationship'] == "FRIEND"]
        if len(next_casualty_id) == 0:
            next_casualty_id = [key for key, value in casualty_list.items() if value['demographics']['rank'] == "VIP"]
        if len(next_casualty_id) == 0:
            next_casualty_id = [key for key, value in casualty_list.items() if value['demographics']['rank'] == "Intel Officer"]
        if len(next_casualty_id) == 0:
            next_casualty_id = [key for key, value in casualty_list.items() if value['demographics']['rank'] == "Marine"]    
        if len(next_casualty_id) == 0:
            next_casualty_id = [key for key, value in casualty_list.items() if value['demographics']['rank'] == "Civilian"]
        
        if len(next_casualty_id) > 0:
            next_casualty = casualty_list[next_casualty_id[0]]
            if len(next_casualty['injuries']) == 0:
                return next_casualty
        else:
            return "no casualties"
 
    # get the injury body system
        data_injury = dict()
        for injury in next_casualty['injuries']:
            if injury == "Burn" or injury == "Forehead Scrape" or injury == "Laceration":
                data_injury =  {"injury":injury, "system":"integumentary"}
                break
            elif injury == "Asthmatic" or injury == "Chest Collapse":
                data_injury =  {"injury":injury, "system":"respiratory"}
                break
            elif injury == "Ear Bleed":
                data_injury =  {"injury":injury, "system":"nervous"}
                break
            elif injury == "Puncture" or injury == "Shrapnel" or injury == "Amputation":
                data_injury =  {"injury":injury, "system":"other"}
                break
            

        return {"casualty":{"id":next_casualty['id'], "name":data_injury['injury'], "system":data_injury['system']}}
        
    '''map between kdmas and treatment predictors (for future work may include casualty and scenario predictors)
    '''
    # for now convert functions are stubs, they will be flushed out later
    def convert_between_kdma_risk_reward_ratio(self, mission, denial, predictor):
        if mission == None and denial == None and predictor != None:# later only return kdma set from its own function
            return {'mission':5, 'denial':3}
        elif predictor == None and mission != None and denial != None:
            if mission >= 8 and mission <= 10:
                return #"low"
            elif mission >= 0 and mission <= 7:
                return "low"           
        else:
            return "incorrect args, no result calculated"

    def convert_between_kdma_resources(self, mission, denial, predictor):
        #return self.convert_between_kdma_risk_reward_ratio(mission, denial, predictor)
        if mission == None and denial == None and predictor != None:# later only return kdma set from its own function
            return {'mission':5, 'denial':3}
        elif predictor == None and mission != None and denial != None:
            if mission >= 8 and mission <= 10:
                return "med"
            elif mission >= 0 and mission <= 7:
                return           
        else:
            return "incorrect args, no result calculated"
    
    def convert_between_kdma_time(self, mission, denial, predictor):
        #return self.convert_between_kdma_risk_reward_ratio(mission, denial, predictor)
        if mission == None and denial == None and predictor != None:# later only return kdma set from its own function
            return {'mission':5, 'denial':3}
        elif predictor == None and mission != None and denial != None:
            if mission >= 8 and mission <= 10:
                return "seconds"
            elif mission >= 0 and mission <= 7:
                return           
        else:
            return "incorrect args, no result calculated"
    
    def convert_between_kdma_system(self, mission, denial, predictor):
        #return self.convert_between_kdma_risk_reward_ratio(mission, denial, predictor)
        if mission == None and denial == None and predictor != None:# later only return kdma set from its own function
            return {'mission':5, 'denial':3}
        elif predictor == None and mission != None and denial != None:
            if mission >= 8 and mission <= 10:
                return "equal"
            elif mission >= 0 and mission <= 7:
                return           
        else:
            return "incorrect args, no result calculated"

    ''' placeholder data needed by hra strategies until functionality is implemented. Currently creates a scenario file
        with kdma associated predictor values (should be learned), predictor values for possible decisions (will be educated guess), kdma values (should be learned)
    '''
    def preprocess(self)->str:
        file = dict()
        
        #file["scenario"] = {"danger":"high", "urgency":"high", "error_prone":"high"}

        file["kdma"] = {"mission":8, "denial":3}

        #file["predictors"] = {"relevance":{"risk_reward_ratio":"low", "time":"seconds", "system":"equal", "resources":"few"}},

        file["treatment"] = {
        #"airway":{"risk_reward_ratio":"med", "resources":"few", "time":"seconds", "system":"respiratory"},
        #"chest seal":{"risk_reward_ratio":"med", "resources":"many", "time":"hours", "system":"respiratory"},
        #"saline lock":{"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"cariovascular"},
        #"intraoss device":{"risk_reward_ratio":"high", "resources":"some", "time":"hours", "system":"cardiovascular"},
        #"iv fluids":{"risk_reward_ratio":"low", "resources":"some", "time":"minutes", "system":["vascular", "renal"]},
        #"hemorrhage control":{"risk_reward_ratio":"med", "resources":"some", "time":"hours", "system":"cardiovascular"},
        #"medications":{"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"all"},
        #"tranexamic acid":{"risk_reward_ratio":"med", "resources":"few", "time":"seconds", "system":"cardiovascular"},
        #"blood products":{"risk_reward_ratio":"high", "resources":"many", "time":"hours", "system":"cardiovascular"},
        #"needle decomp":{"risk_reward_ratio":"high", "resources":"some", "time":"minutes", "system":"respiratory"},
        "CHECK_ALL_VITALS":{"risk_reward_ratio":"low", "resources":"few", "time":"minutes", "system":"all"},
        "hemostatic gauze":{"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"cardiovascular"},
        "tourniquet":{"risk_reward_ratio":"low", "resources":"few", "time":"minutes", "system":"cardiovascular"},
        "pressure bandage":{"risk_reward_ratio":"", "resources":"", "time":"", "system":"integumentary"},
        "decompression needle":{"risk_reward_ratio":"med", "resources":"few", "time":"minutes", "system":"respiratory"},
        "nasopharyngeal airway":{"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"respiratory"}       
        }
        
        #file["casualty"] = {"injury":{"name":"broken arm", "system":"skeleton", "severity":"serious"}}

        #file["casualty_list"] = {"casualty-A": {"age": 22, "sex": "M", "rank": "Military", "hrpmin": 145, "mmhg": 60, "spo2": 85,"rr": 40, "pain": 0}}#,
        #"casualty-B": {"age": 25, "sex": "M", "rank": "Military", "hrpmin": 120, "mmhg": 80, "spo2": 98, "rr": 18, "pain": 6},
        #"casualty-D": {"age": 40, "sex": "M", "rank": "VIP", "hrpmin": 105, "mmhg": 120, "spo2": 99, "rr": 15, "pain": 2},
        #"casualty-E": {"age": 26, "sex": "M", "rank": "Military", "hrpmin": 120, "mmhg": 100, "spo2": 95, "rr": 15, "pain": 10},
        #"casualty-F": {"age": 12, "sex": "M", "rank": "Civilian", "hrpmin": 120, "mmhg": 30, "spo2": 99, "rr": 25, "pain": 3}}
        
        file['injury_list'] = ["Forehead Scrape", "Ear Bleed", "Asthmatic", "Laceration", "Puncture", "Shrapnel", "Chest Collapse", "Amputation", "Burn"]

        json_object = json.dumps(file, indent=2)
        new_file = "temp/newfile.json"
        with open(new_file, "w") as outfile:
            outfile.write(json_object)

        return new_file

    '''
    Call each HRA strategy with scenario info and return a dict of dictionaries, each dictionary 
    corresponds to a possible decision where keys are hra strategies and values are 1 if a 
    strategy returned the decision and 0 otherewise.

    input:
    - json file with scenario, predictors, casualty, and treatment info
    - m, where 0 < m <= M, is the size of the set of predictors to consider when comparing 2 treatments
    - k, where 0 < k <= K, perform tallying on present winner with up to k other treatments

    output:
    - dict of dicts, where each key-value pair is the hra strategy and l if the strategy returned the decision or 0 otherwise
    - tree of search path (not implemented)
    '''
    def hra_decision_analytics(self, file_name:str, m:int=2, k:int=2, search_path=False, rand_seed=0)->dict:

    # extract possible treatments from scenario input file
        f = open(file_name)
        data = json.load(f)
        treatment_idx = list(data['treatment'])
        f.close()

    # extract kdma values from scenario input file
        mission = data['kdma']['mission']
        denial = data['kdma']['denial']

    # get predictor values from kdma values and to scenario file
        risk_reward_ratio = 'risk_reward_ratio'
        resources = 'resources'
        time = 'time'
        system = 'system'

        predictors = {risk_reward_ratio:self.convert_between_kdma_risk_reward_ratio(mission, denial, None),\
                      resources:self.convert_between_kdma_resources(mission, denial, None),\
                      time:self.convert_between_kdma_time(mission, denial, None),\
                      system:self.convert_between_kdma_system(mission, denial, None)}
        
        data['predictors'] = {'relevance':predictors}

    # get next casualty to treat
        next_casualty = self.choose_next_casualty(data['casualty_list'], data['kdma'], data['injury_list'])
        data['casualty'] = next_casualty
        data['casualty']['injury'] = {'system':"unknown"}

    # add predictors and casualty to scenario file
        json_object = json.dumps(data, indent=4)
        new_file = "temp/scene.json"
        with open(new_file, "w") as outfile:
            outfile.write(json_object)

    # update input arg to hold the search path of each strategy
        if search_path:
            search_tree = {'take-the-best':'', 'exhaustive':'', 'tallying':'', 'satisfactory':'', 'one-bounce':''}

    # create a dict for each treatment to hold corresponding HRA strategies
        decision_hra = dict()
        for treatment in treatment_idx:
            decision_hra[treatment] = {'take-the-best':0, 'exhaustive':0, 'tallying':0, 'satisfactory':0, 'one-bounce':0}
        decision_hra["no preference"] = {'take-the-best':0, 'exhaustive':0, 'tallying':0, 'satisfactory':0, 'one-bounce':0}
    
    # call each HRA strategy and store the result with the matching decision list
        take_the_best_result = self.take_the_best(new_file, search_path)#file_name, search_path
        decision_hra[take_the_best_result[0]]['take-the-best'] += 1
        
        exhaustive_result = self.exhaustive(new_file, search_path)#file_name, search_path
        decision_hra[exhaustive_result[0]]['exhaustive'] += 1

        if rand_seed:
            tallying_result = self.tallying(new_file, m, search_path=search_path, seed=rand_seed)#(file_name, m, search_path=search_path, seed=rand_seed)
        else:
            tallying_result = self.tallying(new_file, m, search_path=search_path)#(file_name, m, search_path=search_path)
        decision_hra[tallying_result[0]]['tallying'] += 1

        satisfactory_result = self.satisfactory(new_file, m, seed=rand_seed, search_path=search_path)#file_name, search_path
        decision_hra[satisfactory_result[0]]['satisfactory'] += 1

        one_bounce_result = self.one_bounce(new_file, m, k, search_path)#file_name, search_path
        decision_hra[one_bounce_result[0]]['one-bounce'] += 1

        if search_path:
            search_tree['take-the-best'] = take_the_best_result[2]
            search_tree['exhaustive'] = exhaustive_result[2]
            search_tree['tallying'] = tallying_result[2]
            search_tree['satisfactory'] = satisfactory_result[2]
            search_tree['one-bounce'] = one_bounce_result[2]
        
    # return all hra decision analysis elements       
        if search_path:
            return {
                "decision_hra_dict": decision_hra, 
                "learned_kdma_set": {'mission': mission, 'denial': denial}, 
                "learned_predictors": predictors, 
                "casualty_selected": next_casualty, 
                "decision_comparison_order": search_tree
                }
        else:
            return {
                "decision_hra_dict": decision_hra, 
                "learned_kdma_set": {'mission': mission, 'denial': denial}, 
                "learned_predictors": predictors, 
                "casualty_selected":next_casualty
                }
    
    '''Parent class function that call hra_decision_analytics
    '''
    def analyze(self, scen: Scenario, probe) -> dict[str, DecisionMetrics]:

        # create scenario file
        new_file = self.preprocess()
        with open(new_file, 'r+') as f:
            data = json.load(f)

        casualty_data = dict()
        for ele in scen.state.casualties:
            casualty_data[ele.id] = {
                "id":ele.id, 
                "name":ele.name, 
                "injuries":[l.name for l in ele.injuries], 
                "demographics":{"age":ele.demographics.age, "sex":ele.demographics.sex, 
                                "rank":ele.demographics.rank}, 
                "vitals":{"breathing":ele.vitals.breathing, "hrpmin":ele.vitals.hrpmin}, 
                "tag":ele.tag, "assessed":ele.assessed, "relationship":ele.relationship
                }
    
        data['casualty_list'] = casualty_data
        json_object = json.dumps(data, indent=2)

        with open(new_file, "w") as outfile:
            outfile.write(json_object)
        
        #print("HRA: initial state casualty  info",scen.state.casualties) debug
        
        hra_results = self.hra_decision_analytics(new_file)
        # TODO: Sometimes Casualty Selected is empty/none??
        casualty_selected = hra_results["casualty_selected"]
        if casualty_selected and "id" in casualty_selected:
            priority_casualty = casualty_selected["id"]
        else:
            return {}

        for ele in scen.state.casualties:
            casualty_data = dict()
            casualty_data[ele.id] = {
                "id":ele.id, 
                "name":ele.name, 
                "injuries":[l.name for l in ele.injuries], 
                "demographics":{"age":ele.demographics.age, "sex":ele.demographics.sex, 
                                "rank":ele.demographics.rank}, 
                "vitals":{"breathing":ele.vitals.breathing, "hrpmin":ele.vitals.hrpmin}, 
                "tag":ele.tag, "assessed":ele.assessed, "relationship":ele.relationship
                }
        
            data['casualty_list'] = casualty_data
            json_object = json.dumps(data, indent=2)

            with open(new_file, "w") as outfile:
                outfile.write(json_object)
            
            #print("HRA: initial state casualty  info",scen.state.casualties) debug
            
            hra_results = self.hra_decision_analytics(new_file)
            #print("hra results", hra_results) #debug
            analysis = {}
            
            for decision in probe.decisions:
                if ele.id == decision.value.params.get('casualty', None):
                    if decision.value.name == "CHECK_ALL_VITALS":
                        self.update_metrics(decision, hra_results['decision_hra_dict'], decision.value.name, 
                            ele.id == priority_casualty)
                    elif decision.value.name == "APPLY_TREATMENT":
                        self.update_metrics(decision, hra_results['decision_hra_dict'], decision.value.params['treatment'].lower(),
                            ele.id == priority_casualty)
        
        return {}


    def update_metrics(self, decision: Decision, hra_results: dict, action_name: str, is_priority: bool):
        metrics = {strategy: DecisionMetric(strategy, strategy, int, hra_results[action_name][strategy]) for strategy in HeuristicRuleAnalyzer.STRATEGIES}
        metrics["priority"] = DecisionMetric("priority", "Casualty considered most important", bool, is_priority)
        decision.metrics.update(metrics)
        

"""
if __name__ == '__main__':
    #cwd = Path.cwd()
    #print("cwd", cwd)
    mod_path = Path(__file__).parent
    #print("mod_path:", mod_path)
    #file_path = (mod_path / "scene_one_treatment.json").resolve()
    #file_path = (mod_path / "hra_info.json").resolve()
    #file_path = (mod_path / "scene.json").resolve()
    new_file = (mod_path / "newfile.json").resolve()
    #print("file_path", type(file_path),file_path)
    hra_obj = HeuristicRuleAnalyzer()
    #result = hra_obj.one_bounce(file_path, 2, 3)
    result = hra_obj.hra_decision_analytics(new_file)
    #result = hra_obj.hra_decision_analytics(file_path, 2, rand_seed=0)
    #result = hra_obj.analyze(file_path, 2, rand_seed=0)
    print("result", result)
"""



    