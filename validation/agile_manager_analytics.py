import os
from pathlib import Path
import sys
import gc
import pandas as pd
import numpy as np
import cl4py
import tempfile
from cl4py import Symbol
from cl4py import List as lst
from sklearn.model_selection import train_test_split
import seaborn as sn
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import classification_report

ROOT_DIR = os.path.dirname(os.path.abspath(Path(__file__).parent))

def row_to_hems_program (row, hems, mask=None):
    print(mask)
    with tempfile.NamedTemporaryFile() as fp:
        i = 1
        edges_dict = {}
        feat_idx_dict = {}
        for index, value in row.items():
            if index == "User Strategy Index" and mask != "User Strategy Index":
                fp.write(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(value) + "\""), 'utf-8'))
                #print(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(value) + "\""), 'utf-8'))
                feat_idx_dict[index] = i
                candidate_edges = ["Worker Agent ID"]
                if mask in candidate_edges:
                    candidate_edges.remove(mask)
                edges_dict[i] = candidate_edges
                i += 1
            elif index == "Worker Agent ID" and mask != "Worker Agent ID":
                fp.write(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(value) + "\""), 'utf-8'))
                #print(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(value) + "\""), 'utf-8'))
                feat_idx_dict[index] = i
                candidate_edges = []
                if mask in candidate_edges:
                    candidate_edges.remove(mask)
                edges_dict[i] = candidate_edges
                i += 1
            elif index == "Worker Agent Backlog (No. of Tasks)" and mask != "Worker Agent Backlog (No. of Tasks)":
                fp.write(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_").replace("(", "_").replace(")", "_").replace(".", ""), "\"" + str(value) + "\""), 'utf-8'))
                #print(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_").replace("(", "_").replace(")", "_").replace(".", ""), "\"" + str(value) + "\""), 'utf-8'))
                feat_idx_dict[index] = i
                candidate_edges = ["Worker Agent ID", "Worker Agent Backlog (No. of Effort Units)"]
                if mask in candidate_edges:
                    candidate_edges.remove(mask)
                edges_dict[i] = candidate_edges
                i += 1
            elif index == "Worker Agent Backlog (No. of Effort Units)" and mask != "Worker Agent Backlog (No. of Effort Units)":
                fp.write(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_").replace("(", "_").replace(")", "_").replace(".", ""), "\"" + str(value) + "\""), 'utf-8'))
                #print(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_").replace("(", "_").replace(")", "_").replace(".", ""), "\"" + str(value) + "\""), 'utf-8'))
                feat_idx_dict[index] = i
                candidate_edges = ["Worker Agent ID", "Worker Agent Reputation"]
                if mask in candidate_edges:
                    candidate_edges.remove(mask)
                edges_dict[i] = candidate_edges
                i += 1
            #elif index == "The Backlog Queue":
            #    if isinstance(value, str):
            #        for task_num in value.split(';'):
            #            if task_num != "":
            #                name = "Task{0}".format(task_num)
            #                fp.write(bytes("c{0} = (relation-node {1} :value {2})\n".format(i, name, "\"" + "T" + "\""), 'utf-8'))
            #                #print(bytes("c{0} = (relation-node {1} :value {2})\n".format(i, name, "\"" + "T" + "\""), 'utf-8'))
            #                feat_idx_dict[name] = i
            #                edges_dict[i] = ["Worker Agent Backlog (No. of Effort Units)"]
            #                i += 1
            elif index == "Worker Agent Reputation" and mask != "Worker Agent Reputation":
                fp.write(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(round(value, 1)) + "\""), 'utf-8'))
                #print(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(round(value, 1)) + "\""), 'utf-8'))
                feat_idx_dict[index] = i
                candidate_edges = ["Worker Agent ID"]
                if mask in candidate_edges:
                    candidate_edges.remove(mask)
                edges_dict[i] = candidate_edges
                i += 1
        print(edges_dict)
        for (j, nodes) in edges_dict.items():
            for node in nodes:
                fp.write(bytes("c{0} -> c{1}\n".format(j, feat_idx_dict[node]), 'utf-8'))
                #print(bytes("c{0} -> c{1}\n".format(j, feat_idx_dict[node]), 'utf-8'))
        fp.seek(0)
        return hems.compile_program_from_file(fp.name)

def row_to_hems_program2 (idx, row):
    with open("Programs/HEMS_Agile_Manager/prog{0}.hems".format(idx), mode='w+b') as fp:
        i = 1
        edges_dict = {}
        feat_idx_dict = {}
        for index, value in row.items():
            if index == "User Strategy Index":
                fp.write(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(value) + "\""), 'utf-8'))
                #print(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(value) + "\""), 'utf-8'))
                feat_idx_dict[index] = i
                edges_dict[i] = ["Worker Agent ID"]
                i += 1
            elif index == "Worker Agent ID":
                fp.write(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(value) + "\""), 'utf-8'))
                #print(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(value) + "\""), 'utf-8'))
                feat_idx_dict[index] = i
                edges_dict[i] = []
                i += 1
            elif index == "Worker Agent Backlog (No. of Tasks)":
                fp.write(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_").replace("(", "_").replace(")", "_").replace(".", ""), "\"" + str(value) + "\""), 'utf-8'))
                #print(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_").replace("(", "_").replace(")", "_").replace(".", ""), "\"" + str(value) + "\""), 'utf-8'))
                feat_idx_dict[index] = i
                edges_dict[i] = ["Worker Agent ID", "Worker Agent Backlog (No. of Effort Units)"]
                i += 1
            elif index == "Worker Agent Backlog (No. of Effort Units)":
                fp.write(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_").replace("(", "_").replace(")", "_").replace(".", ""), "\"" + str(value) + "\""), 'utf-8'))
                #print(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_").replace("(", "_").replace(")", "_").replace(".", ""), "\"" + str(value) + "\""), 'utf-8'))
                feat_idx_dict[index] = i
                edges_dict[i] = ["Worker Agent ID", "Worker Agent Reputation"]
                i += 1
            #elif index == "The Backlog Queue":
            #    if isinstance(value, str):
            #        for task_num in value.split(';'):
            #            if task_num != "":
            #                name = "Task{0}".format(task_num)
            #                fp.write(bytes("c{0} = (relation-node {1} :value {2})\n".format(i, name, "\"" + "T" + "\""), 'utf-8'))
            #                #print(bytes("c{0} = (relation-node {1} :value {2})\n".format(i, name, "\"" + "T" + "\""), 'utf-8'))
            #                feat_idx_dict[name] = i
            #                edges_dict[i] = ["Worker Agent Backlog (No. of Effort Units)"]
            #                i += 1
            elif index == "Worker Agent Reputation":
                fp.write(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(round(value, 1)) + "\""), 'utf-8'))
                #print(bytes("c{0} = (percept-node {1} :value {2})\n".format(i, index.replace(" ", "_"), "\"" + str(round(value, 1)) + "\""), 'utf-8'))
                feat_idx_dict[index] = i
                edges_dict[i] = ["Worker Agent ID"]
                i += 1
        for (j, nodes) in edges_dict.items():
            for node in nodes:
                fp.write(bytes("c{0} -> c{1}\n".format(j, feat_idx_dict[node]), 'utf-8'))
                #print(bytes("c{0} -> c{1}\n".format(j, feat_idx_dict[node]), 'utf-8'))


sys.setrecursionlimit(10**6)
# get a handle to the lisp subprocess with quicklisp loaded.
lisp = cl4py.Lisp(cmd=('/usr/local/bin/sbcl', '--dynamic-space-size', '30000', '--script'), quicklisp=True, backtrace=True)

# Start quicklisp and import HEMS package
lisp.find_package('QL').quickload('HEMS')

#load hems and retain reference.
hems = lisp.find_package("HEMS")

am_path = os.path.join(ROOT_DIR, 'data/agile_manager/KDMA is strategy-Decision is Worker Agent ID.xlsx')
print(am_path)

df = pd.read_excel(am_path).drop(['ID', 'Session ID', 'User ID', 'Round'], axis=1)
train, test = train_test_split(df, test_size=0.2)
print(len(train))
print(len(test))

train= train.head(100)
test = test.head(10)

num = 0
for idx, row in train.iterrows():
    if idx >= -1:
        #bn = row_to_hems_program(row, hems)
        row_to_hems_program2(idx, row)
        print()
        print(num)
        num += 1

        hems.push_from_files("Programs/HEMS_Agile_Manager/prog*.hems")
gt_kdmas = []
pred_kdmas = []
metric = "Worker Agent Reputation"
var_name = metric.upper().replace(" ", "_").replace("(", "_").replace(")", "_").replace(".", "")
for idx, row in test.iterrows():
    gt_bn = row_to_hems_program(row, hems)
    bn = row_to_hems_program(row, hems, mask=metric)
    (rec, eme) = hems.remember(hems.get_eltm(), lst(bn), Symbol("+"), 1, Symbol("NIL"))
    print(hems.episode_count(eme))
    i = 0
    for ele in rec:
        if hems.rule_based_cpd_singleton_p(ele):
            if hems.rule_based_cpd_dependent_var(ele) == var_name:
                dep_id = hems.rule_based_cpd_dependent_id(ele)
                print()
                print(hems.rule_based_cpd_dependent_var(ele))
                print(hems.rule_based_cpd_dependent_var(gt_bn[0][i]))
                ret, foundp = hems.get_hash(0, hems.rule_based_cpd_var_value_block_map(gt_bn[0][i]))
                gt_kdma = ret[1][0][0]
                gt_kdmas.append(gt_kdma)
                max_prob = -1
                max_pred = []
                r_pred = []
                for rule in hems.rule_based_cpd_rules(ele):
                    r_prob = hems.rule_probability(rule)
                    if r_prob >= max_prob:
                        index, _ = hems.get_hash(dep_id, hems.rule_conditions(rule))
                        vvbm, _ = hems.get_hash(0, hems.rule_based_cpd_var_value_block_map(ele))
                        #print(vvbm)
                        for vvb in vvbm:   
                            if hems._cdr(hems._car(vvb)) == index:
                                r_pred = hems._car(hems._car(vvb))
                                break
                        #max_pred.append(r_pred)
                        
                        if r_prob == max_prob:
                            max_prob = r_prob
                            max_pred.append(r_pred)
                        else:
                            max_prob = r_prob
                            max_pred = [r_pred]
                        
                pred_kdmas.append(max_pred)
                print()
            i += 1
temp_preds = []
for gt, pred in zip(gt_kdmas, pred_kdmas):
    if gt in pred:
        temp_preds.append(gt)
    else:
        temp_preds.append(pred[0])
pred_kdmas = temp_preds

print()
print("ground truth kdmas:")
print(gt_kdmas)
print("predicted kdmas:")
print(pred_kdmas)
print("Labels:")
labels = list(set(gt_kdmas).union(set(pred_kdmas)))
print(labels)
print()

cm = confusion_matrix(gt_kdmas, pred_kdmas, labels=labels)
print(cm)

print("\nClassification Report\n")
print(classification_report(gt_kdmas, pred_kdmas))

df_cm = pd.DataFrame(cm, labels, labels)
ax = sn.heatmap(df_cm, annot=True, annot_kws={"size": 16}, square=True, cbar=False, fmt='g')
ax.set_title("{0} Prediction Confusion Matrix".format(metric))
#ax.set_ylim(0, 3) #this manually corrects the cutoff issue in sns.heatmap found in matplotlib ver 3.1.1
plt.xlabel("Predicted") 
plt.ylabel("Actual") 
#ax.invert_yaxis() #optional
plt.show()

'''
for idx, row in train.iterrows():
    print(idx)
    row_to_hems_program2(idx, row)
'''
