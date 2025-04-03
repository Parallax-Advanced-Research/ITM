from domain.internal import Decision, AlignmentTarget
from components import DecisionSelector
from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe
from domain.insurance.models.decision import Decision
from domain.insurance.models.decision_value import DecisionValue
from domain.insurance.models.insurance_scenario import InsuranceScenario
from sklearn.neighbors import KNeighborsClassifier


class InsuranceSelector(DecisionSelector):
    def __init__(self, case_base: list[InsuranceTADProbe], single_knn: bool, variant: str = 'aligned', add_kdma: bool = False, add_da_metrics: bool = False):
        self.cb: list[InsuranceTADProbe] = case_base  # this is the training dataset
        self.variant = variant
        self.add_kdma = add_kdma
        self.add_da_metrics = add_da_metrics
        self.single_knn = single_knn # kdma dataset needs 1 knn
        if single_knn:
            self.knn = None
        else:
            self.knn_detectible = None
            self.knn_out_of_pocket = None
            self.knn_preventive = None
            self.knn_pcp = None
            self.knn_telemedicine = None
            self.knn_specialist = None
            self.knn_outpatient_surgery = None
            self.knn_urgent = None
            self.knn_retail_pharmacy = None
            self.knn_mail_order = None

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def convert_expense_type(value):
        if value == "COST IN $":
            return 0
        elif value == "MAXIMUM COST":
            return 1
        elif value == "PERCENT PLAN PAYS":
            return 2
        elif value == "CO-PAY IN $":
            return 3

    @staticmethod
    def convert_employment_type(value):
        if value == 'Hourly':
            return 0
        elif value == 'Salaried':
            return 1
        elif value == 'Bonus':
            return 2

    @staticmethod
    def convert_owns_rents(value):
        if value == 'Owns':
            return 0
        elif value == 'Rents':
            return 1

    @staticmethod
    def convert_travel_location(value):
        return int(value)

    @staticmethod
    def convert_kdma(value):
        if value == 'RISK':
            return 0
        elif value == 'CHOICE':
            return 1

    @staticmethod
    def convert_kdma_value(value):
        if value == 'low':
            return 0
        elif value == 'high':
            return 1


    def convert_to_x_y(self, state, case):
        y = None
        X = [InsuranceSelector.convert_network_status(state.network_status), InsuranceSelector.convert_expense_type(state.expense_type),
             state.children_under_4,
             state.children_under_12, state.children_under_18, state.children_under_26,
             InsuranceSelector.convert_employment_type(state.employment_type),
             state.distance_dm_home_to_employer_hq,
             InsuranceSelector.convert_travel_location(state.travel_location_known),
             InsuranceSelector.convert_owns_rents(state.owns_rents), state.no_of_medical_visits_previous_year,
             state.percent_family_members_with_chronic_condition,
             state.percent_family_members_that_play_sports]
        if case.decisions:
            y = case.decisions[0].value.name

        # add kdma
        if self.add_kdma:
            X.append(InsuranceSelector.convert_kdma(state.kdma))
            X.append(InsuranceSelector.convert_kdma_value(state.kdma_value))

        if self.add_da_metrics:
            X.append(case.decisions[0].metrics['num_med_visits'].to_dict()['value']['value'])
            X.append(case.decisions[0].metrics['family_change'].to_dict()['value']['value'])
            X.append(case.decisions[0].metrics['chance_of_hospitalization'].to_dict()['value']['value'])

        return X, y

    def convert_case_base_to_knn(self, case_base: list[InsuranceTADProbe]):
        X_deductible, y_deductible = [], []
        X_out_of_pocket, y_out_of_pocket = [], []
        X_preventive, y_preventive = [], []
        X_pcp, y_pcp = [], []
        X_telemedicine, y_telemedicine = [], []
        X_specialist, y_specialist = [], []
        X_outpatient_surgery, y_outpatient_surgery = [], []
        X_urgent, y_urgent = [], []
        X_retail_pharmacy, y_retail_pharmacy = [], []
        X_mail_order, y_mail_order = [], []

        for case in case_base:
            state = case.state

            if case.prompt == "DEDUCTIBLE":
                converted_x, converted_y = self.convert_to_x_y(state, case)
                X_deductible.append(converted_x)
                y_deductible.append(converted_y)
            elif case.prompt == "OUT-OF-POCKET MAXIMUM":
                converted_x, converted_y = self.convert_to_x_y(state, case)
                X_out_of_pocket.append(converted_x)
                y_out_of_pocket.append(converted_y)
            elif case.prompt == "PREVENTIVE CARE SERVICES ":
                converted_x, converted_y = self.convert_to_x_y(state, case)
                X_preventive.append(converted_x)
                y_preventive.append(converted_y)
            elif case.prompt == "PRIMARY CARE PHYSICIAN (PCP) ":
                converted_x, converted_y = self.convert_to_x_y(state, case)
                X_pcp.append(converted_x)
                y_pcp.append(converted_y)
            elif case.prompt == "TELE-MEDICINE":
                converted_x, converted_y = self.convert_to_x_y(state, case)
                X_telemedicine.append(converted_x)
                y_telemedicine.append(converted_y)
            elif case.prompt == "SPECIALIST OFFICE VISIT":
                converted_x, converted_y = self.convert_to_x_y(state, case)
                X_specialist.append(converted_x)
                y_specialist.append(converted_y)
            elif case.prompt == "OUTPATIENT SERVICES (SURGERY)":
                converted_x, converted_y = self.convert_to_x_y(state, case)
                X_outpatient_surgery.append(converted_x)
                y_outpatient_surgery.append(converted_y)
            elif case.prompt == "URGENT CARE CENTER":
                converted_x, converted_y = self.convert_to_x_y(state, case)
                X_urgent.append(converted_x)
                y_urgent.append(converted_y)
            elif case.prompt == "RETAIL PHARMACY (UP TO A 30-DAY SUPPLY)":
                converted_x, converted_y = self.convert_to_x_y(state, case)
                X_retail_pharmacy.append(converted_x)
                y_retail_pharmacy.append(converted_y)
            elif case.prompt == "MAIL ORDER (UP TO A 90-DAY SUPPLY)":
                converted_x, converted_y = self.convert_to_x_y(state, case)
                X_mail_order.append(converted_x)
                y_mail_order.append(converted_y)

        return (X_deductible, y_deductible, X_out_of_pocket, y_out_of_pocket, X_preventive, y_preventive, X_pcp, y_pcp,
                X_telemedicine, y_telemedicine, X_specialist, y_specialist, X_outpatient_surgery, y_outpatient_surgery,
                X_urgent, y_urgent, X_retail_pharmacy, y_retail_pharmacy, X_mail_order, y_mail_order)

    def convert_case_base_to_knn_single_knn(self, case_base: list[InsuranceTADProbe]):
        X, y = [], []

        for case in case_base:
            state = case.state
            converted_x, converted_y = self.convert_to_x_y(state, case)
            X.append(converted_x)
            y.append(converted_y)

        return X, y

    def train(self):
        if self.single_knn:
            self.knn = KNeighborsClassifier(n_neighbors=1)

            X, y = self.convert_case_base_to_knn_single_knn(self.cb)
            self.knn.fit(X, y)
        else:
            self.knn_detectible = KNeighborsClassifier(n_neighbors=1)
            self.knn_out_of_pocket = KNeighborsClassifier(n_neighbors=1)
            self.knn_preventive = KNeighborsClassifier(n_neighbors=1)
            self.knn_pcp = KNeighborsClassifier(n_neighbors=1)
            self.knn_telemedicine = KNeighborsClassifier(n_neighbors=1)
            self.knn_specialist = KNeighborsClassifier(n_neighbors=1)
            self.knn_outpatient_surgery = KNeighborsClassifier(n_neighbors=1)
            self.knn_urgent = KNeighborsClassifier(n_neighbors=1)
            self.knn_retail_pharmacy = KNeighborsClassifier(n_neighbors=1)
            self.knn_mail_order = KNeighborsClassifier(n_neighbors=5)

            X_deductible, y_deductible, X_out_of_pocket, y_out_of_pocket, X_preventive, y_preventive, X_pcp, y_pcp, X_telemedicine, y_telemedicine, X_specialist, y_specialist, X_outpatient_surgery, y_outpatient_surgery, X_urgent, y_urgent, X_retail_pharmacy, y_retail_pharmacy, X_mail_order, y_mail_order = self.convert_case_base_to_knn(self.cb)
            self.knn_detectible.fit(X_deductible, y_deductible)
            self.knn_out_of_pocket.fit(X_out_of_pocket, y_out_of_pocket)
            self.knn_preventive.fit(X_preventive, y_preventive)
            self.knn_pcp.fit(X_pcp, y_pcp)
            self.knn_telemedicine.fit(X_telemedicine, y_telemedicine)
            self.knn_specialist.fit(X_specialist, y_specialist)
            self.knn_outpatient_surgery.fit(X_outpatient_surgery, y_outpatient_surgery)
            self.knn_urgent.fit(X_urgent, y_urgent)
            self.knn_retail_pharmacy.fit(X_retail_pharmacy, y_retail_pharmacy)
            self.knn_mail_order.fit(X_mail_order, y_mail_order)

    def select(self, scenario: InsuranceScenario, probe: InsuranceTADProbe, target: AlignmentTarget) -> Decision | int:  # return should prob be just decision, for now return the value
        selected_decision = None
        X_test, y_test = self.convert_to_x_y(probe.state, probe)
        X_test = [X_test]
        predicted = None
        if self.single_knn:
            predicted = self.knn.predict(X_test)
        else:
            if probe.prompt == "DEDUCTIBLE":
                predicted = self.knn_detectible.predict(X_test)
            elif probe.prompt == "OUT-OF-POCKET MAXIMUM":
                predicted = self.knn_out_of_pocket.predict(X_test)
            elif probe.prompt == "PREVENTIVE CARE SERVICES ":
                predicted = self.knn_preventive.predict(X_test)
            elif probe.prompt == "PRIMARY CARE PHYSICIAN (PCP) ":
                predicted = self.knn_pcp.predict(X_test)
            elif probe.prompt == "TELE-MEDICINE":
                predicted = self.knn_telemedicine.predict(X_test)
            elif probe.prompt == "SPECIALIST OFFICE VISIT":
                predicted = self.knn_specialist.predict(X_test)
            elif probe.prompt == "OUTPATIENT SERVICES (SURGERY)":
                predicted = self.knn_outpatient_surgery.predict(X_test)
            elif probe.prompt == "URGENT CARE CENTER":
                predicted = self.knn_urgent.predict(X_test)
            elif probe.prompt == "RETAIL PHARMACY (UP TO A 30-DAY SUPPLY)":
                predicted = self.knn_retail_pharmacy.predict(X_test)
            elif probe.prompt == "MAIL ORDER (UP TO A 90-DAY SUPPLY)":
                predicted = self.knn_mail_order.predict(X_test)

        found_match = False
        vals = []
        for data_key, data_item in probe.state.to_dict().items():
            if data_key in ['val1', 'val2', 'val3', 'val4']:
                vals.append(data_item)
                if data_item == int(predicted[0]):
                    selected_decision = int(predicted[0])
                    found_match = True
                    break
        if not found_match:
            # print(f"predicted value: {predicted[0]}, valid options: {vals}")
            find_closest_val = min(vals, key=lambda x: abs(x - int(predicted[0])))
            # print(f"closest value: {find_closest_val}")
            selected_decision = find_closest_val

        decision = Decision(
            # id_=f'decision_{row_num}_{uuid.uuid4()}',
            value=DecisionValue(name=str(selected_decision))
        )
        return decision
