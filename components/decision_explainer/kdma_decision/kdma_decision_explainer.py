from domain.internal import TADProbe, Decision, Explanation, KDMAs, Action
from components import DecisionExplainer

class KDMADecisionExplainer(DecisionExplainer):
    def __init__(self):
        # each typeof decision will have its own decision explainer variant, e.g. KDMA, exhausive, severity, etc.
        self.variant = "KDMA"
        self.active_action = None
        self.decision_attributes = {}

    def explain_variant(self, decision: Decision, probe: TADProbe):
        # the explanation values dict put in the selected decision (minDecision) by the decision selector
        explanation_values = decision.explanation_values
        
        # in the decision value is the :Action that was selected by the decision selector
        self.active_action : Action = decision.value # the chosen action from the the case constructed from the probe response
        
        similarity = explanation_values["DISTANCE"]

        # kdmas predicted based on the active action 
        predicted_kdmas = explanation_values["BEST_KDMAS"]

        # Extract the nearest neighbor with the highest similarity from the explanation values for the example
        # Just return the first one since the distances are all 0 for now
        top_neighbor_similarity = explanation_values["NEAREST_NEIGHBORS"][0][0]
        top_neighbor = explanation_values["NEAREST_NEIGHBORS"][0][1]
        
        self.decision_attributes.update(decision.metrics)
        # self.decision_attributes.update({"similarity": similarity, "predicted_kdmas": predicted_kdmas, "top_neighbor_similarity": top_neighbor_similarity, "top_neighbor": top_neighbor})
        
        # map the metrics onto the weights to get the related values
        # we can get them from the decision.metrics except for the kdma specific ones

        # the top x weights and their related values
        top_weights = self.process_weights(explanation_values["WEIGHTS"])
        top_properties = self.get_related_values(top_weights, probe)
        explanation_values.update(top_properties)

        explanation = Explanation(self.variant, explanation_values) # the variant could go in the baseline definition
        return explanation
    
    # process the weights dictionary and only return the top 3 weights
    def process_weights(self, weights, top=3):
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        top_weights = sorted_weights[:top]
        return top_weights
    
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