from domain.internal import Scenario, TADProbe, Decision, AlignmentTarget
from components import DecisionSelector
from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe
from domain.insurance.models.insurance_state import InsuranceState
from domain.insurance.models.decision import Decision
from domain.insurance.models.decision_value import DecisionValue
from domain.insurance.models.insurance_scenario import InsuranceScenario
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder


class InsuranceSelector(DecisionSelector):
    def __init__(self, case_base: list[InsuranceTADProbe], variant: str = 'aligned'):
        self.cb: list[InsuranceTADProbe] = case_base  # this is the training dataset
        self.variant = variant
        self.knn = None


    def convert_case_base_to_knn(self, case_base: list[InsuranceTADProbe]):
        def convert_probe(value):
            if value == "DEDUCTIBLE":
                return 0
            elif value == "OUT-OF-POCKET MAXIMUM":
                return 1
            elif value == "PREVENTIVE CARE SERVICES ":
                return 2
            elif value == "PRIMARY CARE PHYSICIAN (PCP) ":
                return 3
            elif value == "TELE-MEDICINE":
                return 4
            elif value == "SPECIALIST OFFICE VISIT":
                return 5
            elif value == "OUTPATIENT SERVICES (SURGERY)":
                return 6
            elif value == "URGENT CARE CENTER":
                return 7
            elif value == "RETAIL PHARMACY (UP TO A 30-DAY SUPPLY)":
                return 8
            elif value == "MAIL ORDER (UP TO A 90-DAY SUPPLY)":
                return 9
        def convert_network_status(value):
            if value == "TIER 1 NETWORK":
                return 0
            elif value == "IN-NETWORK":
                return 1
            elif value == "OUT-OF-NETWORK":
                return 2
            elif value == "GENERIC":
                return 3
            elif value == "ANY CHOICE BRAND":
                return 4
        def convert_expense_type(value):
            if value == "COST IN $":
                return 0
            elif value == "MAXIMUM COST":
                return 1
            elif value == "PERCENT PLAN PAYS":
                return 2
            elif value == "CO-PAY IN $":
                return 3
        def convert_employment_type(value):
            if value == 'Hourly':
                return 0
            elif value == 'Salaried':
                return 1
            elif value == 'Bonus':
                return 2
        def convert_owns_rents(value):
            if value == 'Owns':
                return 0
            elif value == 'Rents':
                return 1
        def convert_travel_location(value):
            return int(value)

        # label_encoder = LabelEncoder()

        X = []
        y = []
        for case in case_base:
            state = case.state
            # X_str = [case.probe_type, state.network_status,
            #          state.expense_type, state.children_under_4, state.children_under_12,
            #          state.children_under_18, state.children_under_26, state.employment_type,
            #          state.distance_dm_home_to_employer_hq, state.travel_location_known,
            #          state.owns_rents, state.no_of_medical_visits_previous_year,
            #          state.percent_family_members_with_chronic_condition, state.percent_family_members_that_play_sports]
            # X.append(label_encoder.fit_transform(X_str))


            X.append([convert_probe(case.prompt), convert_network_status(state.network_status), convert_expense_type(state.expense_type), state.children_under_4, state.children_under_12,
                      state.children_under_18, state.children_under_26, convert_employment_type(state.employment_type), state.distance_dm_home_to_employer_hq, convert_travel_location(state.travel_location_known),
                      convert_owns_rents(state.owns_rents), state.no_of_medical_visits_previous_year, state.percent_family_members_with_chronic_condition, state.percent_family_members_that_play_sports])
            if case.decisions:
                y.append(case.decisions[0].value.name)

        return X, y

    def train(self):
        self.knn = KNeighborsClassifier(n_neighbors=1)
        X, y = self.convert_case_base_to_knn(self.cb)
        self.knn.fit(X, y)

    # scenario is everything but val 1-4, probe is val 1-4, target is kdmas
    def select(self, scenario: InsuranceScenario, probe: InsuranceTADProbe, target: AlignmentTarget) -> Decision | int:  # return should prob be just decision, for now return the value
        selected_decision = None
        X_test, y_test = self.convert_case_base_to_knn([probe])
        predicted = self.knn.predict(X_test)

        # would like to do this, but can't since the test data does not have the decision (correct answer)
        # for decision in probe.decisions:
        #     if decision.value == predicted:
        #         selected_decision = decision

        # so instead I am going to loop through the val1-4 and make sure we selected a valid option
        # going to return None if the predicted value is not in the list of valid options
        for data_key, data_item in probe.state.to_dict().items():
            if data_key in ['val1', 'val2', 'val3', 'val4']:
                if data_item == int(predicted[0]):
                    selected_decision = int(predicted[0])
                    break
        # print(selected_decision)
        return selected_decision
