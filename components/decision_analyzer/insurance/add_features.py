import math


def add_expected_medical_visits_next_year(state):
    percent_of_member_playing_sports = state.percent_family_members_that_play_sports
    percent_of_member_having_chronic_illness = state.percent_family_members_with_chronic_condition
    number_of_medical_visits_previous_year = state.no_of_medical_visits_previous_year
    chance_of_extended_medical_stay = math.ceil(percent_of_member_playing_sports * number_of_medical_visits_previous_year +
                                                percent_of_member_having_chronic_illness * number_of_medical_visits_previous_year +
                                                number_of_medical_visits_previous_year)

    # not sure we want to add to the data_row, or if we want to return it
    # data_row['expected_medical_visits'] = chance_of_extended_medical_stay
    return chance_of_extended_medical_stay


def add_expected_family_change(state):
    children_under_4 = state.children_under_4
    children_under_12 = state.children_under_12
    children_under_18 = state.children_under_18
    children_under_26 = state.children_under_26

    another_baby = 0
    if children_under_26 > 0:
        another_baby = 0  # going to assume no 20 year age gap here
    elif children_under_4 < 2:
        another_baby = 1  # going to assume possible if only 1 child less than 4

    # maybe we can do more with this, but lets worry about that later

    # not sure we want to add to the data_row, or if we want to return it
    # data_row['expected_family_change'] = chance_of_getting_sick
    return another_baby


def add_chance_of_hospitalization(state):
    percent_of_family_members_with_chronic_condition = state.percent_family_members_with_chronic_condition
    number_of_medical_visits_previous_year = state.no_of_medical_visits_previous_year

    chance_of_hospitalization = math.ceil(number_of_medical_visits_previous_year + (number_of_medical_visits_previous_year * (percent_of_family_members_with_chronic_condition / 100)))

    # not sure we want to add to the data_row, or if we want to return it
    # data_row['chance_of_hospitalization'] = chance_of_hospitalization
    return chance_of_hospitalization


def add_expected_annual_coasts(data_row):
    pass