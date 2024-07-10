import pickle as pkl
import json
import os
import os.path as osp

def get_injuries(probe):
    char_list = probe['state']['characters']
    injury_set = set()
    for char in char_list:
        inj_list = char['injuries']
        for inj in inj_list:
            inj_str = "%s %s (%s)" % (inj['location'], inj['name'], inj['severity'])
            injury_set.add(inj_str)
    injury_list = sorted(list(injury_set))
    return injury_list

if __name__ == '__main__':
    print(os.listdir(osp.join('data', 'july_scens')))
    all_inj = []
    for scenario_file in os.listdir(osp.join('data', 'july_scens')):
        print(scenario_file)
        fname = open(osp.join('data', 'july_scens', scenario_file))
        as_json = json.load(fname)
        inj_list = get_injuries(as_json)
        all_inj.extend(inj_list)
        # for inj in inj_list:
        #     print(inj)
        # print('---\n\n\n')
    all_inj = sorted(list(set(all_inj)))
    for inj in all_inj:
        print(inj)
    print('---\n\n\n')