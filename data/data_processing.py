from xgboost_train import *
import copy
from sklearn.model_selection import KFold
import time
import threading, concurrent.futures
import multiprocessing
import logging
import matplotlib.pyplot as plt

'''
This file extracts weights from the data in relation to how they affect the specified features defined in score_keys.
Using the file xgboost_train.py, the weights are extracted and saved to a file in weights/{score_key}/weights_accuracy={acc}.csv
where score_key is the feature being tested and acc is the accuracy of the weights. The specific data used for generating the
weights is also copied into each weights folder. 
'''

pool = concurrent.futures.ThreadPoolExecutor(max_workers=6)
threads = []
processes = []
data_file = 'cleaned_data.csv'
data_folder = "./"
def ingest_data():
    data = {}
    idx = 0
    for file in os.listdir(data_folder):
        if file.endswith("kdma_cases.csv"):
            columns = {}
            with open(data_folder + file, 'r') as f:
                reader = csv.reader(f)
                first = True
                #iterate through each row in the file
                for row in reader:
                    count = 0
                    if first:
                        for ele in row:
                            if ele not in data:
                                data[ele] = {}
                            columns[count] = ele
                            count += 1
                        first = False
                    else:
                        for ele in row:
                            data[columns[count]][idx] = ele
                            count += 1
                        idx += 1
    data_t = {idx: {key: data[key][idx] if idx in data[key] else None for key in data} for idx in data[list(data.keys())[0]]}
    return (data_t)


def clean_data(d):
    categories = set()
    mins = {}
    maxs = {}
    for key in d:
        for key2 in d[key]:
            try:
                d[key][key2] = float(d[key][key2])
                if key2 not in mins:
                    mins[key2] = d[key][key2]
                    maxs[key2] = d[key][key2]
                else:
                    if d[key][key2] < mins[key2]:
                        mins[key2] = d[key][key2]
                    if d[key][key2] > maxs[key2]:
                        maxs[key2] = d[key][key2]
            except:
                if d[key][key2] == "None":
                    continue
                if "," in d[key][key2]:
                    d[key][key2] = d[key][key2].replace(",", "")
                categories.add(key2)
    for key in d:
        for key2 in d[key]:
            if d[key][key2] == "None":
                if key2 not in categories:
                    d[key][key2] = 2*mins[key2] - maxs[key2]
    return d, categories


def trim_weights_to_threshold(df, weights, output_label, threshold_factor):
    new_weights = weights
    while True:
        weights = new_weights
        df = drop_columns_by_weight_threshold(df, weights, output_label, threshold_factor)
        new_weights = xgboost_weights(df, output_label, c)
        if len(new_weights) == len(weights):
            break
    return df

def trim_weights_to_one(df, weights, output_label):
    df = drop_all_columns_by_weight(df, weights, output_label)
    return df

def trim_one_weight(df, weights, output_label):
    df = drop_one_column_by_weight(df, weights, output_label)
    return df


def test_accuracy_t(df, weights, output_label):
    loo = LeaveOneOut()
    gt = []  # ground truth
    y = np.array(df[output_label].tolist())
    X = df.drop(output_label, axis=1)  # removes the decision column
    attributes = X.columns
    results_label = []
    i = 0
    x = loo.split(X)
    l = sum(1 for _ in x)
    current_progress = -1
    print("Performing Accuracy Testing on thread {l}...".format(l=len(weights)))
    start_time = time.time()
    for train_index, test_index in loo.split(X):
        # print progress percentage rounded to 2 decimal places
        progress = int(100 * round(i / l, 2))
        i += 1
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]
        y_pred, x_pred = retrieval(X_test, y_test, X_train, y_train, weights, attributes, k=1, threshold=10)
        results_label.append(y_pred)
        gt.append(y_test)
        if progress != current_progress:
            estimated_time_remaining = int(((time.time() - start_time) / i) * (l - i))
            print(f"Progress on thread {output_label} || {len(weights)}: {progress}% Estimated Time Remaining: {estimated_time_remaining}s")
            current_progress = progress
    results_label = np.array(results_label)
    accuracy = [1 if results_label[i] == y[i] else 0 for i in range(len(results_label))]
    accuracy = sum(accuracy) / len(accuracy)
    save_weights(weights, attributes, accuracy, output_label)
    print(f"\rAccuracy from thread {len(weights)}:", accuracy)


def test_accuracy(df, weights, output_label):
    loo = LeaveOneOut()
    gt = []  # ground truth
    y = np.array(df[output_label].tolist())
    X = df.drop(output_label, axis=1)  # removes the decision column
    attributes = X.columns
    #save_weights(weights, attributes, 0, output_label)
    results_label = []
    i = 0
    x = loo.split(X)
    l = sum(1 for _ in x)
    current_progress = -1
    print("Performing Accuracy Testing...")
    start_time = time.time()
    for train_index, test_index in loo.split(X):
        # print progress percentage rounded to 2 decimal places
        progress = int(100 * round(i / l, 2))
        i += 1
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        dec, y_pred, x_pred = retrieval(X_test, y_test, X_train, y_train, weights, attributes, k=1, threshold=10)
        results_label.append(y_pred)
        gt.append(y_test)
        if progress != current_progress:
            estimated_time_remaining = int(((time.time() - start_time) / i) * (l - i))
            print(f"\rProgress: {progress}% Estimated Time Remaining: {estimated_time_remaining}s", end="")
            current_progress = progress
    results_label = np.array(results_label)
    accuracy = [1 if results_label[i] == y[i] else 0 for i in range(len(results_label))]
    accuracy = sum(accuracy) / len(accuracy)
    save_weights(weights, attributes, accuracy, output_label)
    print(f"\rAccuracy:", accuracy)


def generate_weights(output_label):
    df = pd.read_csv(data_file)
    # df = drop_columns_if_all_unique(df)
    df = drop_columns_by_patterns(df, lable=output_label)
    weights = xgboost_weights(df, output_label, c)
    df = drop_zero_weights(df, weights, output_label)
    weights = xgboost_weights(df, output_label, c)
    total_weights = len(weights)
    finished_weights = []
    if "weights" in os.listdir() and output_label in os.listdir("weights"):
        finished_weights = [int(f.split("-")[0]) for f in os.listdir("weights/" + output_label) if os.path.isdir("weights/" + output_label + "/" + f)]
    if len(finished_weights) == total_weights:
        return
    while len(weights) > 1:
        if len(weights) not in finished_weights:
            #test_accuracy_t(df, weights, output_label)
            #pool.submit(test_accuracy_t, df, weights, output_label)
            #t = threading.Thread(target=test_accuracy_t, args=(df, weights, output_label))
            #threads.append(t)
            p = multiprocessing.Process(target=test_accuracy_t, args=(df, weights, output_label))
            processes.append(p)
        df = trim_one_weight(df, weights, output_label)
        weights = xgboost_weights(df, output_label, c)
    if len(weights) not in finished_weights:
        #t = threading.Thread(target=test_accuracy_t, args=(df, weights, output_label))
        #hreads.append(t)
        p = multiprocessing.Process(target=test_accuracy_t, args=(df, weights, output_label))
        processes.append(p)
        #pool.submit(test_accuracy_t, df, weights, output_label)


def process_data(c):
    score_keys = ["hint.MoralDesert", "hint.maximization"]
    for output_label in score_keys:
        print("Processing", output_label)
        generate_weights(output_label)
        #weights = xgboost_weights(df, output_label, c)
        #test_accuracy(df, weights, output_label)
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for p in processes:
        p.start()
    for p in processes:
        p.join()


def analyze_data():
    data = {"files": {}}
    json_file_template = "weights/{label}/{weight_num}-{accuracy_score}/"
    for label in os.listdir("weights"):
        data[label] = {}
        for run in os.listdir("weights/" + label):
            if not os.path.isdir("weights/" + label + "/" + run):
                continue
            weight_num, accuracy_score = run.split("-")
            weight_num = int(weight_num)
            accuracy_score = float(accuracy_score)
            data[label][weight_num] = accuracy_score
    for label in data:
        if label == "files":
            continue
        print(label)
        print("Max Accuracy:", max(data[label].values()), "at", max(data[label], key=data[label].get), "weights")
        data["files"][label] = json_file_template.format(label=label, weight_num=max(data[label], key=data[label].get), accuracy_score=max(data[label].values()))
        data["files"][label] = json_file_template.format(label=label, weight_num=4, accuracy_score=data[label][4])
        key_values = data[label].items()
        plt.bar([i[0] for i in key_values], [i[1] for i in key_values])
        plt.xlabel("Number of Weights")
        plt.ylabel("Accuracy")
        plt.title(label)
        plt.xticks(range(1, max(data[label].keys()) + 1))
        plt.yticks([round(i, 2) for i in np.arange(0, 1.1, 0.1)])
        plt.savefig(f"weights/{label}/accuracy_plot_for_{label}.png")
        plt.clf()
        ##get peaks
        # in accuracy
        peaks = []
        keys = sorted(data[label].keys())
        for i, key in enumerate(keys):
            print(i, data[label].keys())
            if i == 0:
                if data[label][key] > data[label][keys[i + 1]]:
                    peaks.append(key)
            elif i == len(keys) - 1:
                if data[label][key] > data[label][keys[i - 1]]:
                    peaks.append(key)
            elif data[label][key] > data[label][keys[i-1]] and data[label][key] > data[label][keys[i + 1]]:
                peaks.append(key)

    weights_json = {"kdma_specific_weights": {}, "activity_weights": {}, "standard_weights": {}, "default": 0}
    for folder in os.listdir("weights"):
        feature = folder.split(".")[1]
        json_file = [f for f in os.listdir(data["files"][folder]) if f.endswith(".json")][0]
        weights_json["kdma_specific_weights"][feature] = json.load(open(data["files"][folder] + json_file, 'r'))
    with open("xgboost_weights.json", 'w') as f:
        json.dump(weights_json, f, indent=4)


def build_xgboost_file(m=0, md=0):
    weights_json = {"kdma_specific_weights": {}, "activity_weights": {}, "standard_weights": {}, "default": 0}
    ret = {"maximization": m, "MoralDesert": md}
    for folder in os.listdir("weights"):
        feature = folder.split(".")[1]
        for run in os.listdir("weights/" + folder):
            if not os.path.isdir("weights/" + folder + "/" + run):
                continue
            weight_num, accuracy_score = run.split("-")
            weight_num = int(weight_num)
            accuracy_score = float(accuracy_score)
            if weight_num == ret[feature]:
                json_file = [f for f in os.listdir("weights/" + folder + "/" + run + "/") if f.endswith(".json")][0]
                weights_json["kdma_specific_weights"][feature] = json.load(open("weights/" + folder + "/" + run + "/" + json_file, 'r'))
                break
    with open("xgboost_weights.json", 'w') as f:
        json.dump(weights_json, f, indent=4)


if __name__ == "__main__":
    d = ingest_data()
    d, c = clean_data(d)
    ## print d out as a csv file
    with open(data_file, 'w') as f:
        for key in d[0]:
            f.write(key + ",")
        for key in d:
            f.write("\n")
            for key2 in d[key]:
                f.write(str(d[key][key2]) + ",")
    #process_data(c)
    analyze_data()
    build_xgboost_file(12, 4)
