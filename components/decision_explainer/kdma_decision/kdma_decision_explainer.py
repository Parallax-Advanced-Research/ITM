import ast
from domain.internal import Decision, Explanation
from components import DecisionExplainer
from .explanation_text import generate_explanation_text

class KDMADecisionExplainer(DecisionExplainer):
    def __init__(self):
        super().__init__()
        self.variant = "KDMA_Explainer"
        self.decision = None
        self.explanation = None

    def explain(self, decision: Decision) -> str | None:
        self.decision = decision
        self.explanation = self.get_explanation()
        return self.return_description(self.explanation) if self.explanation else None

    def get_explanation(self):
        return next(
            (item for item in self.decision.explanations if isinstance(item, Explanation) and item.explanation_type == "kdma_estimation"),
            None
        )

    def return_description(self, explanation: Explanation):
        relevant_attributes = self.get_relevant_attributes(explanation)
        new_instance, action_new_instance = self.get_new_instance(explanation, relevant_attributes)
        most_similar_instance, action_most_similar = self.get_most_similar_instance(explanation, relevant_attributes)

        if most_similar_instance:
            output = generate_explanation_text(new_instance, most_similar_instance, action_new_instance, action_most_similar)
        else:
            output = "Could not generate explanation"


        return output

    def get_relevant_attributes(self, explanation):
        weights = explanation.params["weights"]
        return sorted(weights, key=weights.get, reverse=True)[:5]

    def get_new_instance(self, explanation, relevant_attributes):
        decision_action = self.decision.value
        decision_attributes = explanation.params["best_case"]
        new_instance = {k: v for k, v in decision_attributes.items() if k in relevant_attributes}
        new_instance.update(decision_action.params)
        return new_instance, decision_action.name

    def get_most_similar_instance(self, explanation, relevant_attributes):
        similar_cases = explanation.params.get("similar_cases")
        if not similar_cases:
            return None, None

        similar_cases.sort(key=lambda x: x[0])
        similar_case_attributes = similar_cases[0][1]

        if "action" in similar_case_attributes:
            similar_case_action_params = ast.literal_eval(similar_case_attributes.pop("action"))
            similar_case_action_name = similar_case_action_params["name"]
            most_similar_instance = {k: v for k, v in similar_case_attributes.items() if k in relevant_attributes}
            most_similar_instance.update(similar_case_action_params["params"])
            
        elif "action_name" in similar_case_attributes:
            similar_case_action_name = similar_case_attributes.get("action_name")            
            most_similar_instance = {k: v for k, v in similar_case_attributes.items() if k in relevant_attributes}
            most_similar_instance.update({"treatment": similar_case_attributes.get("treatment")})
        else:
            return None, None
        return most_similar_instance, similar_case_action_name