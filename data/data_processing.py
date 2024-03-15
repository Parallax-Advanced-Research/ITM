from xgboost_train import *

valid_fraction = 0.8
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


def process_data(c):
    score_key = "hint.maximization"
    df = pd.read_csv(data_file)
    #df = drop_columns_if_all_unique(df)
    df = drop_columns_by_patterns(df)
    output_label = score_key
    weights = xgboost_weights(df, output_label, c)
    loo = LeaveOneOut()
    gt = []  # ground truth
    y = np.array(df[output_label].tolist())
    X = df.drop(output_label, axis=1)  # removes the decision column
    attributes = X.columns
    save_weights(weights, attributes)
    results_label = []
    i = 0
    x = loo.split(X)
    l = sum(1 for _ in x)
    current_progress = -1
    print("Performing Accuracy Testing...")
    for train_index, test_index in loo.split(X):
        #print progress percentage rounded to 2 decimal places
        progress = int(100 * round(i/l, 2))
        if progress != current_progress:
            print(f"\rProgress: {progress}%", end="")
            current_progress = progress
        i += 1
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        dec, y_pred, x_pred = retrieval(X_test, y_test, X_train, y_train, weights, attributes, k=1, threshold=10)
        results_label.append(y_pred)
        gt.append(y_test)
    results_label = np.array(results_label)
    accuracy = [1 if results_label[i] == y[i] else 0 for i in range(len(results_label))]
    print(f"\rAccuracy:", sum(accuracy)/len(accuracy))
    pass

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
    process_data(c)
