from typing import Any
import json
from domain.internal import AlignmentTarget, AlignmentTargetType
from alignment import kde_similarity

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
                               {kv["kdma"]:kde_similarity.load_kde(kv) for kv in chosen_target["kdma_values"]},
                               AlignmentTargetType.KDE)
        
