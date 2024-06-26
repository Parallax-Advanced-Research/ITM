from domain.internal import TADProbe, Decision, Explanation, KDMAs, Action
from components import DecisionExplainer

class KDMADecisionExplainer(DecisionExplainer):
    def __init__(self):
        # each typeof decision will have its own decision explainer variant, e.g. KDMA, exhausive, severity, etc.
        self.variant = "KDMA"
        self.active_action = None
        self.decision_attributes = {}
        self.nn_attributes = {}        

    def explain_variant(self, decision: Decision, probe: TADProbe):
        # the explanation values dict put in the selected decision (minDecision) by the decision selector
        explanation_values = decision.explanation_values
        
        # in the decision value is the :Action that was selected by the decision selector
        self.active_action : Action = decision.value # the chosen action from the the case constructed from the probe response

        # get the most similar nearest neighbor for comparison
        neighbors = explanation_values["NEAREST_NEIGHBORS"]
        
        # sort the neighbors by similarity
        neighbors.sort(key=lambda x: x[0], reverse=True)

        # get the most similar neighbor which is the first one in the sorted list
        most_similar_neighbor = neighbors[0]

        # get the similarity value
        nn_similarity = most_similar_neighbor[0] # is 'DISTANCE' the average?

        # get the attributes of the nearest neighbor
        self.nn_attributes.update(most_similar_neighbor[1]) # these are values rather than decision metrics object but get_values() can be used to get the values also
        

        self.decision_attributes.update(decision.metrics)
        # we could also get the values from decision metrics objects here
        
        # map the metrics onto the weights to get the related values
        # we can get them from the decision.metrics except for the kdma specific ones

        # the top x weights and their related values
        top_weights = self.process_weights(explanation_values["WEIGHTS"])
        top_properties = self.get_related_values(top_weights, probe)
        
        nn_top_properties = self.get_related_nn_values(top_weights, self.nn_attributes)

       
        # the name of the kdma is the value of the dictionary key        
        active_kdma_name = next(iter(explanation_values["BEST_KDMAS"])) # TODO what if there are multiple
       
        # the kdma value of the nearest neighbor
        nn_kdma = self.nn_attributes[active_kdma_name]

        # the name of the action of the nearest neighbor
        nn_action = most_similar_neighbor[1]["action"] # the action name of the nearest neighbor
        

        # add the values to the explanation values so they can be serialized
        # Maybe we can just send a subset of the values that we need in a new dictionary
        explanation_values.update({"TOP_WEIGHTS":top_weights})        
        explanation_values.update({"TOP_PROPERTIES":top_properties})
        explanation_values.update({"NN_TOP_PROPERTIES":nn_top_properties})
        explanation_values.update({"NN_KDMA":nn_kdma})
        explanation_values.update({"NN_ACTION":nn_action})
        explanation_values.update({"NN_SIMILARITY":nn_similarity})
           

        explanation = Explanation(self.variant,explanation_values)
        return explanation
    



    # process the weights dictionary and only return the top 3 weights
    def process_weights(self, weights, top=3):
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        top_weights = sorted_weights[:top]
        return top_weights
    

    # get the related values of the top weights from the nearest neighbor attributes
    def get_related_nn_values(self, top_weights, nn_attributes):
        related_values = {}
        attributes = nn_attributes
        for weight in top_weights:
            weight_name = weight[0]            
            value = self.get_value_from_object(attributes, weight_name)
            related_values[weight_name] = value
        return related_values

    # get the related values of the top weights from the decision.metrics
    def get_related_values(self, top_weights, probe):
        related_values = {}
        # first see if the related values are in the probe casualty object
        # start by identifying the casualty in the action
        casualty_id = None
        for key, value in self.active_action.params.items():
            if key == "casualty":
                casualty_id = value
                break
        
        # then try and get the related values from casualty object in the probe
        #  in case casualty related attributes are in the top weights        
        if casualty_id is not None:
                for casualty in probe.state.casualties:
                    if casualty.id == casualty_id:
                        for weight in top_weights:
                            weight_name = weight[0]
                            value = self.get_value_from_object(casualty, weight_name)
                            related_values[weight_name] = value
                        self.decision_attributes.update(related_values)

        attributes = self.decision_attributes
        for weight in top_weights:
            weight_name = weight[0]            
            value = self.get_value_from_object(attributes, weight_name)
            related_values[weight_name] = value
        return related_values

    def get_value_from_object(self, obj, attr_name):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == attr_name:
                    return value
                elif isinstance(value, (dict, list)):
                    result = self.get_value_from_object(value, attr_name)
                    if result is not None:
                        return result
        elif isinstance(obj, list):
            for item in obj:
                result = self.get_value_from_object(item, attr_name)
                if result is not None:
                    return result
        elif hasattr(obj, attr_name):
            return getattr(obj, attr_name)
        
        return None