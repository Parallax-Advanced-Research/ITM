import typing

class Explanation():
    def __init__(self, name: str, params: dict[str, typing.Any]):
        self.name: str = name
        self.params: dict[str, typing.Any] = params


    def to_json(self):
        d = dict()
        def get_params(params):
            dd = {}
            for param in self.params:
                dd[param] = params[param]
            return dd
        d['name']  = self.name
        d['params'] = get_params(self.params)
        return d


class DecisionExplanation():
    def __init__(self, decision_type: str):        
        self.decision_type = decision_type
        self.explanation_values= []


    #def __getstate__(self):   # to change the way the object is pickled
    #    return self.__dict__