from typing import List, Any, Dict

class Explanation():
    def __init__(self, decision_type: str, params: Dict[str, Any]):
        self.decision_type: str = decision_type
        self.params: Dict[str, Any] = params

  #def __getstate__(self):   # to change the way the object is pickled
    #    return self.__dict__