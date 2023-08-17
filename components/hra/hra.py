import json
import random


class HRA:

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
    # Given a set of predictors ranked by validity, and n treatments in the decision space, return the treatment that performs 
    best in terms of its predictor values matching with predictor values. In the case where there are multiple highest 
    performing treatments, return "no preference". The comparisons are performed among Σ(n-1) treatment pairs, with each 
    treatment compared to every other treatment once. A comparison stops after the first predictor that discriminates.

    input: 
    - json file with scenario, predictors, casualty, and treatment info, where predictors preferences are ranked according to validity

    output:
    - decision
    '''
    def take_the_best(self, file_name:str)->tuple:

    # prep the input
    # - open the file
        f = open(file_name)

    # get dict from data and convert treatment dict to list
        data = json.load(f)
        treatment_idx = list(data['treatment'])

    # if there is only a single treatment in the decision space
        if len(treatment_idx) == 1:
            return (treatment_idx[0], data['treatment'][treatment_idx[0]])

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
                predictor_val = data['predictors']['relevance'][predictor][0]

    # - - if a treatment wins the round add 1 to its score and end the comparison
    # - - - special case for system predictor
                if predictor == "system":
                    if (treatment0[predictor] == data['casualty']['injury']['system'] or treatment0[predictor] == "all") and\
                        not (treatment1[predictor] == data['casualty']['injury']['system'] or treatment1[predictor] == "all"):
                        treatment_sums[battle[0]] += 1
                        break

                    elif (treatment1[predictor] == data['casualty']['injury']['system'] or treatment1[predictor] == "all") and\
                        not (treatment0[predictor] == data['casualty']['injury']['system'] or treatment0[predictor] == "all"):
                        treatment_sums[battle[1]] += 1
                        break           
                            
    # - - - normal case for predictor
                else:
                    if treatment0[predictor] == predictor_val and not (treatment1[predictor] == predictor_val):
                        treatment_sums[battle[0]] += 1
                        break
                    elif treatment1[predictor] == predictor_val and not (treatment0[predictor] == predictor_val):
                        treatment_sums[battle[1]] += 1
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
            return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]])
        else:
            return ("no preference", "")

    '''
    Exhaustive: search strategy that ranks ALL decisions in decisions space according to 
    ALL relevance predictor values and returns the highest ranked treatment

    input: 
    - json file thats describes scenario, predictor, casualty, decision space

    output:
    - decision
    '''

    def exhaustive(self, file_name:str)->tuple:

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
                predictor_val = data['predictors']['relevance'][predictor][0]

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

    # return winner
    # - get max value(s) index from sums
        max_val = max(all_treatment_sum)
        sequence = range(len(all_treatment_sum))
        list_indices = [index for index in sequence if all_treatment_sum[index] == max_val]

    # - if the max isn't tied
        if len(list_indices) == 1:

    # - - return treatment, info pair corresponding to max index
            return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]])

    # - if the max is tied return "no preference"
        else:
            return ("no preference", "")

    '''
    Tallying: # Given a set of randomly selected predictors m, where m ⊆ M (the complete set of predictors), and n treatments 
    in the decision space, return the treatment that performs best in terms of its predictor values matching with predictor 
    predictor values. The comparisons are performed among Σ(n-1) treatment pairs, with each treatment compared to every other 
    treatment once. If one treatment performs better add 1 to its sum and continue to the next treatment pair. If two 
    treatments perform equally with respect to the set m, and the size of m < the size of M, randomly select one of the 
    remaining predictors from M, comparing the treament pair against this new predictor; if the size of m equals that of M, 
    continue to the next treatement pair. Return the treatment that performed best relative to the other treatments, or 
    "no preference" if there no clear winner.

    input: 
    - json file with scenario, predictors, casualty, and treatment info
    - m, where 0 < m <= M, is the size of the set of predictors to consider when comparing 2 treatments

    output: decision
    '''
    def tallying(self, file_name:str, m:int, seed=None)->tuple:

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
            #for h in rand_predictor_idx:
            for h in rand_predictor_idx[:m]:
                predictor = predictor_idx[h]
                predictor_val = data['predictors']['relevance'][predictor][0]

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

    # - - else if the two treatment scores are equal
            else:
    # - - - get M\m set of random predictors
                rrand_predictor_idx =  rand_predictor_idx[m:]

    # - - - while size of set M\m is not empty
                for i in rrand_predictor_idx:
                    rpredictor = predictor_idx[i]
                    rpredictor_val = data['predictors']['relevance'][rpredictor][0]

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
            return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]])
        else:
            return ("no preference", "")

    '''
    Call each HRA strategy with scenario info and return the strategies that resulted in each decision

    input:
    - json file with scenario, predictors, casualty, and treatment info
    - m, where 0 < m <= M, is the size of the set of predictors to consider when comparing 2 treatments

    output:
    - dict, where each key-value pair is the decision and a list of each of its applicable HRA strategies
    '''
    def hra_decision_analytics(self, file_name:str, m:int)->dict:

    # extract possible treatments from scenario input file
        f = open(file_name)
        data = json.load(f)
        treatment_idx = list(data['treatment'])
        f.close()

    # create a list for each treatment to hold corresponding HRA strategies
        decision_hra = dict()
        for treatment in treatment_idx:
            decision_hra[treatment] = list()

    # call each HRA strategy and store the result with the matching decision list
        decision_hra[self.exhaustive(file_name)[0]].append("exhaustive")
        decision_hra[self.take_the_best(file_name)[0]].append("take-the-best")
        decision_hra[self.tallying(file_name, 2)[0]].append("tallying")

    # return all lists
        return decision_hra

    # for now convert functions are stubs, they will be flushed out later
    def convert_between_kdma_risk_reward_ratio(self, convert_arg):
        if len(convert_arg) > 1:
            return "low"
        elif len(convert_arg) == 1:
            return [1, 2, 3, 4, 5 , 6]
        else:
            return "wrong args"

    def convert_between_kdma_resources(self, convert_arg):
        self.convert_between_kdma_risk_reward_ratio(convert_arg)
    
    def convert_between_kdma_time(self, convert_arg):
        self.convert_between_kdma_risk_reward_ratio(convert_arg)
    
    def convert_between_kdma_system(self, convert_arg):
        self.convert_between_kdma_risk_reward_ratio(convert_arg)
