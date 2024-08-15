import math
import random
from typing import Any
import copy
import yaml
import os
import networkx as nx
import matplotlib.pyplot as plt
from typing import Optional, Union
import json
class Edge:
    pass

class Node:
    _name: str
    _edges: list[Edge] = []
    _id: str
    def __init__(self, name: str, id: str=None):
        self._name = name
        if id:
            self._id = id
        else:
            self._id = name
        self._edges = []

    def add_edge(self, edge: Edge):
        self._edges.append(edge)

    @property
    def edges(self):
        return self._edges

    @property
    def id(self):
        return self._id
    @id.setter
    def id(self, value):
        self._id = value

    @edges.setter
    def edges(self, value):
        self._edges = value
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def __repr__(self):
        return f"{self._name}"

    def __str__(self):
        return f"{self._name}"

class Edge:
    _source: Node
    _target: Node
    _name: str
    def __init__(self, source: Node, name: str,target: Node):
        self._source = source
        self._name = name
        self._target = target

    @property
    def source(self):
        return self._source

    @property
    def target(self):
        return self._target

    @property
    def name(self):
        return self._name

    def __repr__(self):
        return f"{self._source.name} -{self._name}-> {self._target.name}"

    def __str__(self):
        return f"{self._source.name} -{self._name}-> {self._target.name}"

class FeatureTerm:
    nodes: list[Node] = []
    unique_nodes: dict[str, int] = {}
    edges: list[Edge] = []
    name = "Lame"
    _root: Node = None
    objects: dict[Node: str] = {}
    kdmas: set[str] = set()
    def __init__(self):
        self.nodes = []
        self.unique_nodes = {}
        self.edges = []
        self.name = "Lame"
        self._root = None
        self.objects = {}
        self.kdmas = set()


    def add_node(self, node: Node):
        #Nodes have unique names, maintains a dict of node names and counts
        if node.name not in self.unique_nodes:
            self.unique_nodes[node.name] = 0
        self.unique_nodes[node.name] += 1
        self._root = None
        if node.id == node.name:
            node.id = f"{node.id}_{self.unique_nodes[node.name]}"
        self.nodes.append(node)

    def add_edge(self, source: Union[Node, Edge], target: Node=None):
        if not target:
            self.edges.append(source)
            if source not in source.source.edges:
                source.source.edges.append(source)
        else:
            e = Edge(source, target)
            source.add_edge(e)
            self.edges.append(e)
        self._root = None

    def add_ambiguous(self, thing: Union[Node, Edge]):
        t = type(thing)
        if t is Node:
            self.add_node(thing)
        elif t is Edge:
            self.add_edge(thing)
        else:
            raise Exception(f"Unknown type: {t}")

    @property
    def root(self):
        if self._root is None:
            nodes = [n for n in self.nodes if n not in [e.target for e in self.edges]]
            if len(nodes) != 1:
                raise Exception("More than one root node")
            self._root = nodes[0]
        return self._root

    def to_dict(self): #convert to dict, edges denote moving a level deeper in the dictionary
        retval = {}
        queue = list()
        queue.append((self.root, []))
        visited_nodes = set()
        while len(queue) > 0:
            head, keys = queue.pop()
            temp = retval
            for key in keys:
                temp = temp[key]
            for edge in head.edges: #add edges to the dictionary
                if not edge.target.edges:
                    if edge.source.name in temp:
                        if type(temp[edge.source.name]) is dict:
                            temp[edge.source.name][edge.target.name] = None
                        elif type(temp[edge.source.name]) is list:
                            temp[edge.source.name].append(edge.target.name)
                        else:
                            temp[edge.source.name] = [edge.target.name]
                    else:
                        if not type(temp) == dict:
                            pass
                        temp[edge.source.name] = edge.target.name
                else:
                    if edge.source.name not in temp:
                        temp[edge.source.name] = {}
                    elif type(temp[edge.source.name]) is not dict:
                        if type(temp[edge.source.name]) is list:
                            print("Here")
                        temp[edge.source.name] = {temp[edge.source.name]: None}
                    if edge.target.name == "age":
                        pass
                    if edge.target not in visited_nodes:
                        queue.append((edge.target, keys + [edge.source.name]))
                        visited_nodes.add(edge.target)


        return retval


    def to_graphviz_txt(self):
        #print a graphviz representation of the feature term
        retval = ""
        for node in self.nodes:
            retval += f"{node.name} [label=\"{node.name}\"];\n"
        for edge in self.edges:
            retval += f"{edge.source.name} -> {edge.target.name};\n"
        return retval

    def to_graphviz(self):
        #print a graphviz representation of the feature term
        #CURRENTLY NODES WITH SAME NAMES ARE OVERWRITTEN TODO: FIX THIS
        G = nx.DiGraph()
        labels = {}
        edge_labels = {}
        for node in self.nodes:
            G.add_node(node.id)
            labels[node.id] = node.name
        for edge in self.edges:
            G.add_edge(edge.source.id, edge.target.id, label=edge.name)
            edge_labels[(edge.source.id, edge.target.id)] = edge.name
        #space out the nodes
        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, labels=labels)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
        plt.show()


    def __str__(self):
        return f"Nodes: {len(self.nodes)} Edges: {len(self.edges)}"

    def __repr__(self):
        #print a graphviz representation of the feature term
        return f"digraph {{\n{self.to_graphviz_txt()}\n}}"

    def deepcopy(self):
        new_term = FeatureTerm()
        #new_root = Node(self.root.name)
        #new_term.add_node(new_root)
        for node in self.nodes:
            new_node = Node(node.name, node.id)
            new_term.add_node(new_node)
        for edge in self.edges:
            source = [x for x in new_term.nodes if x.id == edge.source.id][0]
            target = [x for x in new_term.nodes if x.id == edge.target.id][0]
            e = Edge(source, edge.name, target)
            new_term.add_edge(e)
        for obj in self.objects:
            n = [x for x in new_term.nodes if x.name == obj][0]
            new_term.objects[n.name] = n
        new_term.kdmas = self.kdmas
        return new_term

def combine_nodes(x: Node, y: Node, term: FeatureTerm):
    heads = [(e.source, e) for e in term.edges if e.target == x or e.target == y]
    tails = [(e.target, e) for e in term.edges if e.source == x or e.source == y]
    new_node = Node(x.name)
    term.nodes = [x for x in term.nodes if x.name != new_node.name]
    term.unique_nodes.pop(new_node.name)
    term.add_node(new_node)
    for head, edge in heads:
        head.edges = [e for e in head.edges if e.target != x and e.target != y]
        e = Edge(head, edge.name, new_node)
        term.add_edge(e)
    for tail, edge in tails:
        tail.edges = [e for e in tail.edges if e.source != x and e.source != y]
        e = Edge(new_node, edge.name, tail)
        term.add_edge(e)
    return new_node

def read_in_yaml(filename: str) -> dict[str, list[FeatureTerm]]:
    scenario = None
    with open(filename, 'r') as stream:
        try:
            scenario = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    passive_term = FeatureTerm()


    state = scenario['state']
    scenes = scenario['scenes']
    [s for s in scenes if s['id'] == 'P1'][0]['state'] = state
    queue = list()
    # iterate through state, alternating from node to edge_label and back
    # for t in [t for t in state if t != "unstructured"]:
    #     queue.append((state_node, t, state[t]))
    # while len(queue) > 0:
    #     head, tail, d = queue.pop()
    #     if type(d) is dict:
    #         n = Node("")
    #         e = Edge(head, tail, n)
    #         passive_term.add_node(n)
    #         passive_term.add_edge(e)
    #         for t in [t for t in d if t != "unstructured"]:
    #             piece = d[t]
    #             queue.append((n, t, piece))
    #     elif type(d) is list:
    #         for item in d:
    #             if type(item) is dict:
    #                 if "id" in item:
    #                     n = Node(item["id"])
    #                     if n.name not in passive_term.objects:
    #                         passive_term.objects[n.name] = n
    #                     else:
    #                         n = passive_term.objects[n.name]
    #                 else:
    #                     n = Node(tail[:-1])
    #                 e = Edge(head, tail, n)
    #                 passive_term.add_node(n)
    #                 passive_term.add_edge(e)
    #                 for t in [t for t in item if t != "unstructured"]:
    #                     piece = item[t]
    #                     queue.append((n, t, piece))
    #             else:
    #                 pass
    #         pass
    #     else:
    #         n = Node(d)
    #         e = Edge(head, tail, n)
    #         passive_term.add_node(n)
    #         passive_term.add_edge(e)

    terms = {}
    for scene in scenes:
        header = scene.pop("id")
        scene_term = FeatureTerm()
        scene_node = Node(header)
        scene_term.add_node(scene_node)
        action_terms = []
        for t in [t for t in scene if t != "unstructured"]:  # add all state variables to the passive term
            queue.append((scene_node, t, scene[t], scene_term))  # add the state variable to the queue
        while len(queue) > 0:  # while there are items in the queue
            head, tail, d, term = queue.pop()
            if tail == "kdma_association":  # save to terms with kdma as key
                path = [tail]
                nodes = [(e.source, e) for e in term.edges if e.target==head]
                while len(nodes) == 1:
                    temp, temp_e = nodes[0]
                    path = [temp_e.name] + path
                    nodes = [(e.source, e) for e in term.edges if e.target==temp]
                if len(nodes) > 0:
                    raise Exception("Something went wrong")
                for kdma in d:
                    p = path + [kdma]
                    p = "?>?".join(p)
                    if p not in terms:
                        terms[p] = []
                    term.kdmas.add(p)
            if tail == "action_mapping":  # split term, one for each action
                for action in d:
                    header = "action"
                    # new_term = term.deepcopy()
                    # new_head = [x for x in new_term.nodes if x.name == head.name][0]
                    # new_term.root.name = new_term.root.name + "_" + action['action_id']
                    new_term = FeatureTerm()
                    new_head = Node("Placeholder")
                    action_terms.append(new_term)
                    new_term.add_node(new_head)
                    # for kdma in new_term.kdmas:
                    #     if kdma not in terms:
                    #         terms[kdma] = []
                    #     terms[kdma].append(new_term)
                    #     if term in terms[kdma]:
                    #         terms[kdma].remove(term)
                    queue.append((new_head, header, action, new_term))
                continue
            if type(d) is dict:
                n = Node("")
                e = Edge(head, tail, n)
                if head.name == "state":
                    print("here")
                term.add_node(n)
                term.add_edge(e)
                for t in [t for t in d if t != "unstructured"]:
                    piece = d[t]
                    queue.append((n, t, piece, term))
            elif type(d) is list:
                for item in d:
                    if type(item) is dict:
                        if "id" in item:
                            n = Node(item["id"])
                            if n.name not in term.objects:
                                term.objects[n.name] = n
                            else:
                                n = term.objects[n.name]
                        else:
                            n = Node(tail[:-1])
                        e = Edge(head, tail, n)
                        term.add_node(n)
                        term.add_edge(e)
                        for t in [t for t in item if t != "unstructured"]:
                            piece = item[t]
                            queue.append((n, t, piece, term))
                    else:
                        n = Node(item)
                        if n.name not in term.objects:
                            term.objects[n.name] = n
                        else:
                            n = term.objects[n.name]
                        e = Edge(head, tail, n)
                        term.add_node(n)
                        term.add_edge(e)
            else:
                n = Node(d)
                e = Edge(head, tail, n)
                term.add_node(n)
                term.add_edge(e)

        for term in action_terms:
            root_n, edge_n = [(x.target, x.name) for x in term.root.edges][0]
            new_term = scene_term.deepcopy()
            new_term_root = new_term.root
            for node in [n for n in term.nodes if n != term.root]:
                new_term.add_node(node)
            for edge in [e for e in term.edges if e.source != term.root]:
                new_term.add_edge(edge)
            for kdma in term.kdmas:
                new_term.kdmas.add(kdma)

            new_edge = Edge(new_term_root, edge_n, root_n)


            new_term.add_edge(new_edge)
            new_term.root.name = new_term.root.name + "_" + pi(new_term, ['action', 'action_id'])[0][1]
            for obj in [o for o in new_term.objects if o in [x.name for x in term.nodes]]:
                nodes = [x for x in term.nodes if x.name == obj]
                true_node = new_term.objects[obj]
                for node in nodes:
                    true_node = combine_nodes(node, true_node, new_term)
                new_term.objects[obj] = true_node
            for kdma in new_term.kdmas:
                if kdma not in terms:
                    terms[kdma] = []
                terms[kdma].append(new_term)
        #add in passive term
    return terms
# def read_in_yaml(filename: str) -> dict[str:list[FeatureTerm]]:
#     #NEEDS TO HANDLE LOOPS BETTER TODO: FIX THIS
#     scenario = None
#     with open(filename, 'r') as stream:
#         try:
#             scenario = yaml.safe_load(stream)
#         except yaml.YAMLError as exc:
#             print(exc)
#     passive_term = FeatureTerm()
#     state_node = Node("state")
#     passive_term.add_node(state_node)
#
#     state = scenario['state']
#     scenes = scenario['scenes']
#
#     queue = list()
#     #iterate through state, alternating from node to edge_label and back
#     for t in [t for t in state if t != "unstructured"]:  # add all state variables to the passive term
#         queue.append((state_node, t, state[t]))  # add the state variable to the queue
#     while len(queue) > 0:  # while there are items in the queue
#         head, tail, d = queue.pop()  # pop the first item off the queue
#         #if t is Node, create a new node and add it to the edge that is head
#         n = Node(tail)
#         passive_term.add_node(n)
#         passive_term.add_edge(head, n) #consider saving edges in the head node as well. This is a bit redundant but aides lookup
#         if type(d) is dict:
#             for t in [t for t in d if t != "unstructured"]:
#                 piece = d[t]
#                 queue.append((n, t, piece))
#         elif type(d) is list:  # UPDATE
#             for item in d:
#                 if type(item) is dict:
#                     header = item.pop("id", item.pop("type", item.pop("name",None)))  #This is specific to this yaml, update for new yamls
#                     queue.append((n, header, item))
#                 else: # leafs
#                     leaf = Node(item)
#                     passive_term.add_node(leaf)
#                     passive_term.add_edge(n, leaf)
#         else: # d should be a leaf, make it a node and add the edge
#             leaf = Node(d)
#             passive_term.add_node(leaf)
#             passive_term.add_edge(n, leaf)
#
#     #passive_term.to_graphviz()
#     terms = {}
#     for scene in scenes:
#         header = scene.pop("id")
#         scene_term = FeatureTerm()
#         scene_node = Node(header)
#         scene_term.add_node(scene_node)
#         for t in [t for t in scene if t != "unstructured"]:  # add all state variables to the passive term
#             queue.append((scene_node, t, scene[t], scene_term))  # add the state variable to the queue
#         while len(queue) > 0:  # while there are items in the queue
#             head, tail, d, term = queue.pop()  # pop the first item off the queue
#             if tail == "parameters":
#                 pass
#             #if t is Node, create a new node and add it to the edge that is head
#             if tail == "kdma_association":  # save to terms with kdma as key
#                 path = [head.name, tail]
#                 nodes = [e.source for e in term.edges if e.target==head]
#                 while len(nodes) == 1:
#                     temp = nodes[0]
#                     path = [temp.name] + path
#                     nodes = [e.source for e in term.edges if e.target==temp]
#                 if len(nodes) > 0:
#                     raise Exception("Something went wrong")
#                 for kdma in d:
#                     p = path[1:] + [kdma]
#                     p = "?>?".join(p)
#                     if p not in terms:
#                         terms[p] = []
#                     terms[p].append(term)
#                 pass
#             if tail == "action_mapping":  # split term, one for each action
#                 for action in d:
#                     header = "action"
#                     new_term = term.deepcopy()
#                     new_head = [x for x in new_term.nodes if x.name == head.name][0]
#                     new_term.root.name = new_term.root.name + "_" + action['action_id']
#                     queue.append((new_head, header, action, new_term))
#                 continue
#             n = Node(tail)
#             term.add_node(n)
#             if head.name == "P1":
#                 pass
#             term.add_edge(head, n)
#             if type(d) is dict:
#                 for t in [t for t in d if t != "unstructured"]:
#                     piece = d[t]
#                     queue.append((n, t, piece, term))
#             elif type(d) is list:
#                 for item in d:
#                     if type(item) is dict:
#                         header = item.pop("id", item.pop("type", item.pop("name", item.pop("probe_id", None))))  #This is specific to this yaml, update for new yamls
#                         queue.append((n, header, item, term))
#                     else:
#                         leaf = Node(item)
#                         term.add_node(leaf)
#                         term.add_edge(n, leaf)
#             else: # d should be a leaf, make it a node and add the edge
#                 leaf = Node(d)
#                 term.add_node(leaf)
#                 term.add_edge(n, leaf)
#     for kdma in terms:
#         #add in passive term
#         for term in terms[kdma]:
#             root_n = term.root
#             new_passive_term = passive_term.deepcopy()
#             for node in new_passive_term.nodes:
#                 node.id = node.name
#                 term.add_node(node)
#             for edge in new_passive_term.edges:
#                 term.add_edge(edge)
#             term.add_edge(root_n, new_passive_term.root)
#             done = []
#             bad_types = [bool, int, float, list, dict, tuple, type(None)]
#             bad_matches = ['visible', 'military_branch', 'military_disposition', 'race', 'sex', 'visited', 'quantity', 'reusable', 'type', 'id', 'name', 'unstructured', 'status', 'severity', 'location', 'spo2', 'heart_rate', 'breathing', 'mental_status', 'ambulatory', 'avpu', 'rapport', 'demographics', 'tag', 'injuries', 'vitals', 'probe_id', 'choice', 'kdma_association', 'action_id', 'action_type', 'character_id', 'unstructured', 'mission_type', 'medical_policies', 'sim_environment', 'decision_environment', 'supplies', 'characters', 'next_scene', 'end_scene_allowed', 'persist_characters', 'action_mapping', 'restricted_actions', 'transitions']
#             values = ["major", "White", "US Army", 'left chest', "Chest Collapse", 'right calf', "extreme", "minor", "Allied US", "Amputation"]
#             for x, y in [(x, y) for x in term.nodes for y in term.nodes if x != y and x.name == y.name and type(x.name) not in bad_types and not any(x.name in sublist for sublist in [bad_matches, values]) and x.name != x.name.upper()]:
#                 if (x, y) not in done:
#                     combine_nodes(x, y, term)
#                     done.append((y, x))
#             pass
#     return terms



def LID(Sd, p, D, C, pred):
    try:
        if stopping_condition(Sd, C):
            c = cases(Sd)
            return c, D
        else:
            fd, v, al = select_leaf(p, Sd, C, [pred] + [x[0] for x in D])
            D_ = add_path(pi(p, fd), D)
            Sd_ = disciminatory_set(D_, Sd)
            C_ = create_solution_class(pred, Sd_)
            c = LID(Sd_, p, D_, C_, pred)
            return c
    except Exception as e:
        if e.args and e.args[0] == 'No matching classes found':
            return None
        else:
            raise e



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

def get_leafs(p, max_depth=7): #this one is for feature terms, not dicts
    leafs = []
    iterator = []
    head = p.root
    for node, edge in [(x.target, x) for x in head.edges]:
        iterator.append(([edge.name], node))
    while len(iterator) > 0:
        l, p = iterator.pop()
        if len(l) > max_depth:
            continue
        n = l[-1]
        if p.edges:
            for node, edge in [(x.target, x) for x in p.edges]:
                iterator.append((l + [edge.name], node))
        else: #leaf
            leafs.append((l, p.name))
    return leafs

def get_leafs2(p): #dicts
    leafs = []
    iterator = []
    for key in p:
        iterator.append(([key], p[key]))
    while len(iterator) > 0:
        l, p = iterator.pop()
        n = l[-1]
        if type(p) == dict:
            for key in p:
                iterator.append((l + [key], p[key]))
        elif type(p) == list:
            for item in p:
                iterator.append((l, item))
        else:
            leafs.append((l, p))
    return leafs

def check_class(class_, fd):
    #check that all partitions in class_ ahve the same value for pi(fd)
    for partition in class_:
        partition = class_[partition]
        for case in partition['cases']:
            case = case[[x for x in case.keys()][0]]
            low = partition['k'][0]
            high = partition['k'][1]
            val = pi(case, fd)[0][1]
            if low == high == None and val != None:
                return False
            elif low == high == None and val == None:
                pass
            elif not (partition['k'][0] <= pi(case, fd)[0][1] <= partition['k'][1]):
                return False
    return True

def select_leaf(p, Sd, C, avoid):
    leafs = get_leafs(p)
    default = [['action', 'probe_id'], ['next_scene'], ['transitions', 'probes']]
    "find all leafs in dictionary p"

    # find the leaf with the minimum RLM distance from the discriminatory set
    min_distance = float('inf')
    infs = []
    all_leafs = []
    min_leaf = None
    leafs = [l for l in leafs if l[0] not in avoid]#+default]
    if not check_class(C, avoid[0]):
        raise Exception("Class is not valid")
    for f, v in leafs:
        try:
            leaf_class = create_solution_class(f, Sd)
            if not check_class(leaf_class, f):
                raise Exception("Class is not valid")
            distance = compute_rlm_distance(leaf_class, C)
            all_leafs.append((f, distance))
        except AssertionError as e:
            #logger.debug('leaf feture' + str(f) + ' is not found in the discriminatory set')
            create_solution_class(f, Sd)
            raise e
            continue
        if distance == math.inf and min_leaf is None:
            infs.append(f)
        if distance < min_distance:
            min_distance = distance
            min_leaf = f
    if min_leaf is None and len(infs) > 0:
        min_leaf = random.choice(infs)
    elif min_leaf is None:
        for a in avoid:
            vals = []
            for case in Sd:
                #print(pi(Sd[case], a), end=" ")
                vals.append(pi(Sd[case], a)[0][1])
            if len(set(vals)) > 1:
                print(a, vals)
        raise Exception("No leafs exist")
    return min_leaf, min_distance, all_leafs

def pi2(case, fd):
    '''returns the value of the path fd in the case'''
    orig_fd = copy.copy(fd)
    fd = copy.copy(fd)
    while len(fd) > 0:
        if type(fd) == tuple:
            raise Exception("fd is a tuple")
        if type(fd) == str:
            pass
        f = fd.pop(0)
        if type(case) == dict:
            if f not in case:
                return [(None, None)]
            case = case[f]
        elif type(case) == list:
            retval = []
            for item in case:
                retval += pi(item, [f]+fd)
            return [(orig_fd, x[1]) for x in retval]
    return [(orig_fd, case)]

def pi(case, fd):
    if type(case) is not FeatureTerm:
        raise Exception("pi is only for feature terms")
    head = case.root
    counter = 0
    while counter < len(fd):
        heads = [x.target for x in head.edges if x.name == fd[counter]]
        if len(heads) == 0:
            return([(fd, None)])
        head = heads[0]
        counter += 1
    return [(fd, head.name)]
def add_path(pi, D):
    return D + pi

def disciminatory_set(D_, Sd):
    '''

    :param D_: Paths to ensure that the discriminatory set is satisfied
    :param Sd_: Previous discriminatory set
    :return: New discriminatory set

    May need to add in tolerances instead of equality, play around with it some

    '''
    Sd_ = copy.copy(Sd)
    bad_cases = []
    for case in Sd_:
        for p in D_:
            paths = pi(Sd_[case], p[0])
            found = False
            for p_ in paths:
                if p[1] == p_[1]:
                    found = True
                    break
            if not found:
                bad_cases.append(case)
    for case in bad_cases:
        Sd_.pop(case)

    return Sd_

def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def create_solution_class(feature, cb):
    '''
    Need to quantile continuous feature values
    currently quantiles contain equal number of values, but could be changed to equal range of values

    :param feature:
    :param cb:
    :return:
    '''
    if feature == ['action', 'choice']:
        pass
    threshold = 0.1  # threshold for continuous vs discrete, 0.1 means 10% of values must be unique
    # first, get all values of feature in cb
    values = []
    quantile_values = []
    for case in cb:
        vals = pi(cb[case], feature)
        if vals:
            for val in vals:
                if val:
                    values.append(val[1])
    none_flag = False
    if None in values:
        none_flag = True
        values = [x for x in values if x is not None]
    values = sorted([x for x in values if type(x) is not list] + [x for y in values if type(y) is list for x in y])
    #identify if values are a continuous set or discrete set, by comparing unique values to total number of values
    if len(values) == 0 and none_flag:
        return {-1: {'k': [None, None], 'cases': [{x: cb[x]} for x in cb]}}
    try:
        set(values)
    except:
        vals = pi(cb[case], feature)
    quantiled = False
    if len(values) == 0:
        print("here")
    if len(set(values)) / len(values) > 1 - threshold:  # continuous
        #discretize the values using quantiles
        num_values = len(values)
        test_1 = list(split(values, math.floor(1/threshold)))
        test = [[x[0], x[-1]] for x in test_1 if x]
        quantile_values = [values[math.floor(i * num_values * threshold)] for i in range(1, (math.floor(1/threshold)))]
        quantile_values = [values[0]] + sorted(list(set(quantile_values))) + [values[-1]] #add the min and max values
        classes = {i: {'k': test[i], 'cases': []} for i in range(len(test))}
    else:  # discrete
        quantile_values = sorted(list(set(values)))
        classes = {i: {'k': [quantile_values[i], quantile_values[i]], 'cases': []} for i in range(len(quantile_values))}
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
        #vals = retval[1]
        #if vals is not None and type(vals) is not list:
        #    vals = [vals]
        for key, vals in retval:
            if vals is not None:
                try:
                    if type(vals) is not list:
                        vals = [vals]
                    for val in vals:
                        for x in [y for y in classes.keys() if y != -1]:
                            if classes[x]['k'][0] <= val <= classes[x]['k'][1]:
                                added = True
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
    test = [x for x in new_classes if new_classes[x]['cases'] == []]
    test2 = [x for x in cb if x not in [list(y.keys())[0] for x in new_classes for y in new_classes[x]['cases']]]
    if test2:
        pass
    return new_classes


def compute_rlm_distance(partition1_ : dict[Any, int], partition2_: dict[Any, int]) -> float:
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
    partition1 = {}
    for k, v in partition1_.items():
        for a in v['cases']:
            key = list(a.keys())[0]
            if key not in partition1:
                partition1[key] = []
            partition1[key].append(k)
    partition2 = {}
    for k, v in partition2_.items():
        for a in v['cases']:
            key = list(a.keys())[0]
            if key not in partition2:
                partition2[key] = []
            partition2[key].append(k)
    #partition1 = {list(a.keys())[0]: k for k, v in partition1_.items() for a in v['cases']}
    #partition2 = {list(a.keys())[0]: k for k, v in partition2_.items() for a in v['cases']}
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
    if objCt != len(keys2):
        pass
    if not(objCt == len(keys2)):
        print("here")
    assert(objCt == len(keys2))
    assert(len(set(keys1) - set(keys2)) == 0)
    assert(len(set(keys2) - set(keys1)) == 0)
    values1 = set([x for y in partition1.values() for x in y])
    values2 = set([x for y in partition2.values() for x in y])
    m = len(values1)
    n = len(values2)
    Pij = []
    for i in range(m):
        Pij.append([0] * n)
    Pi = [0] * m
    Pj = [0] * n
    slice = 1 / objCt
    for item, i_s in partition1.items():
        if item not in partition2: #Re-evaluate this
            continue
        j_s = partition2[item]
        if len(i_s) > 1 or len(j_s) > 1:
            print(i_s, j_s)
        for i in i_s:
            Pi[i] += slice
        for j in j_s:
            if j >= len(Pj):
                pass
            Pj[j] += slice
        for i in i_s:
            for j in j_s:
                Pij[i][j] += slice

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
    return 2 * IPAintersectB - (IPa + IPb)
    #return 2 - ((IPb + IPa) / IPAintersectB)

def negEntropy(prob: float) -> float:
    if prob == 0:
        return 0
    if prob < 0:
        raise Error()
    return prob * math.log2(prob) * -1



if __name__ == "__main__":
    # print current path
    prev_path = os.getcwd().split('\\')[:-1]
    added_path = ["scenarios", "dryrun", "dryrun-adept-DryRunEval.MJ1-train.yaml"]
    added_path = ["scenarios", "dryrun"]
    new_path = ('\\').join(prev_path + added_path)
    folder_path = ('\\').join(prev_path + added_path)
    files = os.listdir(folder_path)
    all_terms = {}
    for file in files:
        if file.endswith(".yaml") and "train" in file and "adept" in file:
            yaml_id = [x for x in file.split("-") if any(char.isdigit() for char in x)][0]
            print(yaml_id)
            kdma_terms = read_in_yaml(folder_path + "\\" + file)
            for kdma in kdma_terms: #this is where the terms are stored
                if kdma not in all_terms:
                    all_terms[kdma] = {}
                terms = kdma_terms[kdma]
                for term in terms:
                    all_terms[kdma][yaml_id + "_" + term.root.name] = term #this is where the feature terms are stored
            # for kdma in kdma_terms:
            #     if kdma not in dict_terms:
            #         dict_terms[kdma] = {}
            #     terms = kdma_terms[kdma]
            #     for term in terms:
            #         d_term = term.to_dict()
            #         dict_terms[kdma][yaml_id + "_" + term.root.name] = d_term.pop(term.root.name)
    # json.dump(dict_terms, open(folder_path + "\\" + "terms.json", "w"))
    descriptions = {}
    for kdma in all_terms:
        descriptions[kdma] = []
        for c in all_terms[kdma]:
            loo = {}
            for case in all_terms[kdma]:
                if case != c:
                    loo[case] = all_terms[kdma][case]
            loo_p = create_solution_class(kdma.split("?>?"), loo)
            print(compute_rlm_distance(loo_p, loo_p))


            ret_val = LID(loo, all_terms[kdma][c], [], loo_p, kdma.split("?>?"))
            descriptions[kdma].append(ret_val[1])
            print("OUT")
            print(ret_val[1])
            print(len(descriptions[kdma]))
        print()
    print(descriptions)
    json.dump(descriptions, open(folder_path + "\\" + "descriptions.json", "w"))
    # for kdma in kdma_terms:
    #     terms = kdma_terms[kdma]
    #     kdma_partition = create_solution_class(kdma, terms)
    #     LID(terms,terms[0], {}, kdma_partition, kdma)