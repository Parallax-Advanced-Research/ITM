from typing import Any
import json
from domain.internal import AlignmentTarget, AlignmentTargetType
import pickle
import codecs

def get_named_alignment_target(name: str) -> Any:
    if name.startswith("soartech-dryrun-"):
        fname = "data/soartech-dryrun-alignment-targets.json"
        targets = []
        with open(fname, "r") as f:
            targets = json.loads(f.read())
        target_id = name.replace("soartech-dryrun-", "")
        chosen_target = [t for t in targets if t.get("id", None) == target_id]
        if len(chosen_target) > 0:
            chosen_target = chosen_target[0]
        else:
            chosen_target = None
        if chosen_target is None:
            try:
                chosen_target = targets[int(target_id)]
            except:
                raise Error(f"Can't find target {target_id} in {fname}.")
        return AlignmentTarget(chosen_target["id"], 
                               [kv["kdma"] for kv in chosen_target["kdma_values"]],
                               {kv["kdma"]:get_kde(kv) for kv in chosen_target["kdma_values"]},
                               AlignmentTargetType.KDE)
        
def get_kde(kdma_value_dict: dict):
    kde_str = kdma_value_dict["kdes"]["globalnormx_localnormy"]["kde"]
    return pickle.loads(codecs.decode(kde_str.encode(), "base64"))