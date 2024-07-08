import math
import random
from typing import Any
from util import logger
import copy


def LID(Sd, p, D, C, pred):
    if stopping_condition(Sd, C):
        c = cases(Sd)
        return c
    else:
        fd, v = select_leaf(p, Sd, C, pred)
        D_ = add_path(pi(p, fd), D)
        Sd_ = disciminatory_set(D_, Sd)
        c = LID(Sd_, p, D_, C, pred)
        return c

def cases(Sd):
    '''convert Sd to a list of cases in Sd'''
    return [c for k, c in Sd.items()]

def stopping_condition(Sd, C):
    '''
    stop when all cases in Sd are in the same class within C
    '''
    Sd_c = [c for c in Sd]
    classes = [c for c in C if any(x in [ca_num for ca in C[c]['cases'] for ca_num in ca] for x in Sd_c)]
    if len(classes) == 1:
        return True
    elif len(classes) == 0:
        raise(Exception("No matching classes found"))
    else:
        return False

def select_leaf(p, Sd, C, avoid):
    leafs = []
    "find all leafs in dictionary p"
    iterator = []
    for key in p:
        iterator.append(([key], p[key]))
    while len(iterator) > 0:
        l, p = iterator.pop()
        n = l[-1]
        if type(p) == dict:
            for key in p:
                iterator.append((l+[key], p[key]))
        elif type(p) == list:
            for item in p:
                iterator.append((l, item))
        else:
            leafs.append((l,p))

    # find the leaf with the minimum RLM distance from the discriminatory set
    min_distance = float('inf')
    infs = []
    min_leaf = None
    leafs = [l for l in leafs if l[0] != avoid]
    for f, v in leafs:
        try:
            leaf_class = create_solution_class(f, Sd)
            distance = compute_rlm_distance(leaf_class, C)
        except AssertionError as e:
            logger.debug('leaf feture' + str(f) + ' is not found in the discriminatory set')
            continue
        if distance == math.inf and min_leaf is None:
            infs.append(f)
        if distance < min_distance:
            min_distance = distance
            min_leaf = f
        else:
            print("distance is greater than min_distance")
    if min_leaf is None and len(infs) > 0:
        min_leaf = random.choice(infs)
    elif min_leaf is None:
        raise Exception("No leafs exist")
    return min_leaf, min_distance

def pi(case, fd):
    '''returns the value of the path fd in the case'''
    orig_fd = copy.copy(fd)
    fd = copy.copy(fd)
    while len(fd) > 0:
        if type(fd) == tuple:
            pass
            raise Exception("fd is a tuple")
        f = fd.pop(0)
        if type(case) == dict:
            if f not in case:
                return None, None
            case = case[f]
        elif type(case) == list:
            retval = []
            for item in case:
                retval += pi(item, [f]+fd)
            return retval
    return (orig_fd, case)

def add_path(pi, D):
    return D + [pi]

def disciminatory_set(D_, Sd):
    '''

    :param D_: Paths to ensure that the discriminatory set is satisfied
    :param Sd: Previous discriminatory set
    :return: New discriminatory set

    May need to add in tolerances instead of equality, play around with it some

    '''
    Sd_ = {}
    for case in Sd:
        for p in D_:
            path = pi(case, p[0])
            if p[1] == path[1]:
                Sd_[case] = Sd[case]

    return Sd_

def create_solution_class(feature, cb):
    '''
    Need to quantile continuous feature values
    currently quantiles contain equal number of values, but could be changed to equal range of values

    :param feature:
    :param cb:
    :return:
    '''
    threshold = 0.1  # threshold for continuous vs discrete, 0.1 means 10% of values must be unique
    # first, get all values of feature in cb
    values = []
    quantile_values = []
    for case in cb:
        val = pi(cb[case], feature)
        if val:
            values.append(val[1])
    none_flag = False
    if None in values:
        none_flag = True
        values = [x for x in values if x]
    values = sorted(values)
    #identify if values are a continuous set or discrete set, by comparing unique values to total number of values
    if len(values) == 0 and none_flag:
        return {-1: {'k': [None, None], 'cases': [{x: cb[x]} for x in cb]}}
    if len(set(values)) / len(values) < threshold:  # continuous
        #discretize the values using quantiles
        num_values = len(values)
        quantile_values = [values[math.floor(i * num_values * threshold)] for i in range(1, (math.floor(1/threshold)))]
        quantile_values = [values[0]] + list(set(quantile_values)) + [values[-1]]
    else:  # discrete
        quantile_values = list(set(values))
    if len(quantile_values) == 40:
        pass
    classes = {i: {'k': quantile_values[i:i+2], 'cases': []} for i in range(len(quantile_values) - 1)}
    if none_flag:
        classes[-1] = {'k': [None, None], 'cases': []}
    #condense classes if any k values have 0 range
    # pops = []
    # for i in range(len(classes)):
    #     if i in pops:
    #         continue
    #     if classes[i]['k'][0] == classes[i]['k'][1]: #this class has no range
    #         #remove this class, and adjust the k values of the other classes
    #         j = i + 1
    #         while j < len(classes) and classes[i]['k'][0] == classes[j]['k'][1]:
    #             j += 1
    #         j -= 1
    #         [pops.append(k) for k in range(i, j+1)]
    # for i in pops:
    #     try:
    #         if len(classes) == 1:
    #             break
    #         classes.pop(i)
    #     except:
    #         pass
    #renumber the classes so there are no integer breaks
    if not cb:
        logger.warn("empty case base")
    for case in cb:
        retval = pi(cb[case], feature)
        try:
            key, val = pi(cb[case], feature)
        except Exception as e:
            pass
        if val is not None:
            try:
                for x in [x for x in classes.keys() if x != -1]:
                    if classes[x]['k'][0] <= val <= classes[x]['k'][1]:
                        classes[x]['cases'].append({case: cb[case]})
                        break
            except Exception as e:
                pass
        else:
            if none_flag:
                classes[-1]['cases'].append({case: cb[case]})
            else:
                pass #this should never happen, a none value got through the filter
    # number classes from 0 to n
    keys = [x for x in classes]
    new_classes = {}
    for k in keys:
        new_classes[keys.index(k)] = classes.pop(k)
    return new_classes


def compute_rlm_distance(partition1 : dict[Any, int], partition2: dict[Any, int]) -> float:
    '''

    :param partition1: dictionary[class_num]{k: class value, cases: list[case]}
    :param partition2: ^^^
    :return: distance between the two partitions
    '''
    val_to_class1 = {}
    val_to_class2 = {}
    par1 = {}
    par2 = {}
    #partition1 = {list(a.keys())[0] : k for k, v in partition1.items() for a in v}
    #partition2 = {list(a.keys())[0] : k for k, v in partition2.items() for a in v}
    new_partition1 = {}
    partition1 = {list(a.keys())[0]: k for k, v in partition1.items() for a in v['cases']}
    partition2 = {list(a.keys())[0]: k for k, v in partition2.items() for a in v['cases']}
    #for key in partition1:
    #    if partition1[key] not in val_to_class1:
    #        val_to_class1[partition1[key]] = len(val_to_class1)
    #    partition1[key] = val_to_class1[partition1[key]]
    #for key in partition2:
    #    if partition2[key] not in val_to_class2:
    #        val_to_class2[partition2[key]] = len(val_to_class2)
    #    partition2[key] = val_to_class2[partition2[key]]
    keys1: list[Any]
    keys2: list[Any]
    keys1 = partition1.keys()
    keys2 = partition2.keys()
    objCt = len(keys1)
    if objCt == 0:
        pass
    assert(objCt == len(keys2))
    assert(len(set(keys1) - set(keys2)) == 0)
    assert(len(set(keys2) - set(keys1)) == 0)
    values1 = set(partition1.values())
    values2 = set(partition2.values())
    m = len(values1)
    n = len(values2)
    Pij = []
    for i in range(m):
        Pij.append([0] * n)
    Pi = [0] * m
    Pj = [0] * n
    slice = 1 / objCt
    for item, i in partition1.items():
        if item not in partition2: #Re-evaluate this
            continue
        j = partition2[item]
        try:
            Pi[i] += slice
        except Exception as e:
            pass
        try:
            Pj[j] += slice
        except Exception as e:
            pass
        print(i, j, Pij)
        try:
            Pij[i][j] += slice
        except Exception as e:
            pass
    IPa = 0
    for i in range(m):
        IPa += negEntropy(Pi[i])
    IPb = 0
    for j in range(n):
        IPb += negEntropy(Pj[j])
    IPAintersectB = 0
    for i in range(m):
        for j in range(n):
            IPAintersectB += negEntropy(Pij[i][j])
    if IPAintersectB == 0:
        return math.inf
    return 2 - ((IPb + IPa) / IPAintersectB)

def negEntropy(prob: float) -> float:
    if prob == 0:
        return 0
    if prob < 0:
        raise Error()
    return prob * math.log2(prob) * -1



if __name__ == "__main__":
    class TestLID():
        #def test_stopping_condition(self):
            #self.assertTrue(stopping_condition({}))
            #self.assertTrue(stopping_condition({1: 1}))
            #self.assertTrue(stopping_condition({1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9}))
            #self.assertFalse(stopping_condition({1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10}))

        def test_select_leaf(self):
            p = {1: 1, 2: 2, 3: 3, 4: 4}
            Sd = {1: 1, 2: 2, 3: 3}
            C = {1: 1, 2: 2, 3: 3}
            assert(select_leaf(p, Sd, C) ==  (1, 0))

        def test_pi(self):
            case = {1: {2: {3: 4}}}
            fd = [1, 2, 3]
            assert(pi(case, fd) ==  [{3: 4}])

        def test_add_path(self):
            assert(add_path([1, 2, 3], [4, 5, 6]) ==  [4, 5, 6, [1, 2, 3]])

        def test_discriminatory_set(self):
            assert(disciminatory_set([1, 2, 3], [4, 5, 6]) ==  {})

        def test_LID(self):
            Sd = {1: 1, 2: 2, 3: 3}
            p = {1: 1, 2: 2, 3: 3, 4: 4}
            D = [1, 2, 3]
            C = {1: 1, 2: 2, 3: 3}
            assert(LID(Sd, p, D, C) ==  [1, 2, 3])

        def test_compute_rlm_distance(self):
            partition1 = {0: {'k': 1, 'cases': [{1: []}, {2: []}, {3: []}]}, 1: {'k': 2, 'cases': [{4: []}, {5: []}, {6: []}]}}
            partition2 = {0: {'k': 1, 'cases': [{1: []}, {2: []}, {3: []}]}, 1: {'k': 2, 'cases': [{4: []}, {5: []}, {6: []}]}}
            assert(compute_rlm_distance(partition1, partition2) ==  0)
            '''
            Partition on A:

            Class1:{C0, C1}
            
            Class1:{C2, C3}
            
            Class1:{C4, C5}
            
            Class1:{C6, C7}
            
            Class1:{C8, C9}
            
            Partition on B:
            Class1:{C1, C3, C5, C7, C9}

            Class1:{C0, C2, C4, C6, C8}
            
            Partition on C:
            Class1:{C0, C1}

            Class1:{C2, C3}
            
            Class1:{C4, C5}
            
            Class1:{C6, C7}
            
            Class1:{C8, C9}
            '''
            partitionA = {0: {'k': 1, 'cases': [{0: []}, {1: []}]}, 1: {'k': 2, 'cases': [{2: []}, {3: []}]}, 2: {'k': 3, 'cases': [{4: []}, {5: []}]}, 3: {'k': 4, 'cases': [{6: []}, {7: []}]}, 4: {'k': 5, 'cases': [{8: []}, {9: []}]}}
            partitionB = {0: {'k': 1, 'cases': [{1: []}, {3: []}, {5: []}, {7: []}, {9: []}]}, 1: {'k': 2, 'cases': [{0: []}, {2: []}, {4: []}, {6: []}, {8: []}]}}
            partitionC = {0: {'k': 1, 'cases': [{0: []}, {1: []}]}, 1: {'k': 2, 'cases': [{2: []}, {3: []}]}, 2: {'k': 3, 'cases': [{4: []}, {5: []}]}, 3: {'k': 4, 'cases': [{6: []}, {7: []}]}, 4: {'k': 5, 'cases': [{8: []}, {9: []}]}}
            print(compute_rlm_distance(partitionA, partitionC))
            print(compute_rlm_distance(partitionB, partitionC))
            print(compute_rlm_distance(partitionA, partitionB))
            print(compute_rlm_distance(partitionA, partitionA))
            print(compute_rlm_distance(partitionB, partitionB))
            print(compute_rlm_distance(partitionC, partitionC))


    # Run the tests
    test = TestLID()
    #test.test_select_leaf()
    #test.test_pi()
    #test.test_add_path()
    #test.test_discriminatory_set()
    #test.test_LID()
    test.test_compute_rlm_distance()




