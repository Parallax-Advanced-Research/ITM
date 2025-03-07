import math


def add_all_features():
    pass


def _add_expected_medical_visits_next_year(data_row):
    percent_of_member_playing_sports = data_row['percent_of_member_playing_sports']
    percent_of_member_having_chronic_illness = data_row['percent_of_member_having_chronic_illness']
    number_of_medical_visits_previous_year = data_row['number_of_medical_visits_previous_year']
    chance_of_extended_medical_stay = math.ceil(percent_of_member_playing_sports * number_of_medical_visits_previous_year +
                                                percent_of_member_having_chronic_illness * number_of_medical_visits_previous_year +
                                                number_of_medical_visits_previous_year)

    # not sure we want to add to the data_row, or if we want to return it
    data_row['expected_medical_visits'] = chance_of_extended_medical_stay
    return data_row


def _add_expected_family_change(data_row):
    children_under_4 = data_row['children_under_4']
    children_under_12 = data_row['children_under_12']
    children_under_18 = data_row['children_under_18']
    children_under_26 = data_row['children_under_26']

    chance_of_getting_sick = children_under_4 * 0.50 + children_under_12 * 0.25 + children_under_18 * 0.10 + children_under_26 * 0.05

    # not sure we want to add to the data_row, or if we want to return it
    data_row['expected_family_change'] = chance_of_getting_sick
    return data_row


def _add_chance_of_hospitalization(data_row):
    percent_of_family_members_with_chronic_condition = data_row['percent_of_family_members_with_chronic_condition']
    number_of_medical_visits_previous_year = data_row['number_of_medical_visits_previous_year']

    chance_of_hospitalization = math.ceil(number_of_medical_visits_previous_year + (number_of_medical_visits_previous_year * (percent_of_family_members_with_chronic_condition / 100)))

    # not sure we want to add to the data_row, or if we want to return it
    data_row['chance_of_hospitalization'] = chance_of_hospitalization
    return data_row


def __add_expected_annual_coasts(data_row):
    pass