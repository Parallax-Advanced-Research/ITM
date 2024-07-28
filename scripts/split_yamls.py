import yaml
import glob

LAST_SCENE = {"index": 1, "end_scene_allowed": True, "action_mapping": []}

def split_yamls(scenario_file: str, source: str):
    monster_scenario: dict = None
    index = 0
    for fname in glob.glob(scenario_file):
        with open(fname, "r") as infile:
            monster_scenario = yaml.safe_load(infile.read())
        new_scenario = {"name": monster_scenario["name"]}
        index = index + 1
        new_scenario["id"] = f"{source}-{index}"
        new_scenario["scenes"] = [fix_actions(monster_scenario["scenes"][0]), LAST_SCENE]
        new_scenario["state"] = monster_scenario["state"]
        state = monster_scenario["state"]
        with open(f"online-{source}-train-{index}.yaml", "w") as outfile:
            outfile.write(yaml.dump(new_scenario))
        for scene in monster_scenario["scenes"][1:]:
            if not "state" in scene:
                continue
            index = index + 1
            scene["index"] = 0
            new_scenario["id"] = f"{source}-{index}"
            new_scenario["scenes"] = [fix_actions(scene), LAST_SCENE]
            new_scenario["state"] = state
            state_update = scene.pop("state")
            state["characters"] = state_update["characters"]
            if "supplies" in state_update:
                state["supplies"] = state_update["supplies"]
            apply_state_update(state, state_update, "threat_state")
            apply_state_update(state, state_update, "mission")
            if "environment" in state_update:
                apply_state_update(state["environment"], state_update["environment"], "sim_environment")
                apply_state_update(state["environment"], state_update["environment"], "decision_environment")
            with open(f"online-{source}-train-{index}.yaml", "w") as outfile:
                outfile.write(yaml.dump(new_scenario))

def fix_actions(scene: dict):
    for mapping in scene["action_mapping"]:
        if "next_scene" in mapping:
            mapping.pop("next_scene")
    return scene
            
            
def apply_state_update(state, state_update, key):
    if key in state_update:
        if key not in state:
            state[key] = dict()
        for (k, v) in state_update[key].items():
            state[key][k] = v