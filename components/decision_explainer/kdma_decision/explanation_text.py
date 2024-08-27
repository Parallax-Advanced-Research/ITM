import pandas as pd
import re
from .select_template import select

def convert_to_percentage(match):
    value = float(match.group(0)) * 100
    return f"{value:.0f}%"

def generate_explanation_text(new_instance, most_similar_instance, action_new_instance, action_most_similar):
    pattern = r'\b0\.\d+'
    df = pd.read_csv("components/decision_explainer/kdma_decision/case_base.csv")
    descriptions = generate_descriptions(df, most_similar_instance)

    joined_descriptions = ", ".join(descriptions)

    if joined_descriptions:
        first_description = generate_first_description(new_instance, most_similar_instance, action_new_instance, action_most_similar)
        final_description = f"{first_description}. In a prior case where {joined_descriptions}."
        complete_desc = add_and_to_last_comma(final_description)
    else:
        complete_desc = "No matching descriptions found."

    complete_desc = re.sub(pattern, convert_to_percentage, complete_desc)
    return complete_desc

def generate_descriptions(df, most_similar_instance):
    descriptions = []
    for attributeName, value in most_similar_instance.items():
        attribute, casualty_name = parse_attribute(attributeName)
        attribute_type = get_attribute_type(df, attribute)

        if attribute_type is None:
            continue

        if attribute_type == 'boolean':
            descriptions.extend(get_boolean_descriptions(df, attribute, value))
        elif attribute_type in {'continuous', 'categorical', 'categorical-continuous'}:
            descriptions.append(get_continuous_description(df, attribute, value, casualty_name))
        elif attribute_type in {'multicategorical', 'binary'}:
            descriptions.extend(get_multicategorical_descriptions(df, attribute, value))

    return descriptions

def parse_attribute(attributeName):
    if '.' in attributeName and attributeName != 'HRA Strategy.time-resources.take-the-best':
        return attributeName.split('.', 1)
    else:
        return attributeName, 'Unknown'

def get_attribute_type(df, attribute):
    attribute_types = df.loc[df['attribute'] == attribute, 'type']
    return attribute_types.values[0] if not attribute_types.empty else None

def get_boolean_descriptions(df, attribute, value):
    if isinstance(value, str):
        value = value.lower() == 'true'
    filtered_df = df[(df['attribute'] == attribute) & (df['text_value'] == value)]
    return filtered_df['description'].tolist() if not filtered_df.empty else []

def get_continuous_description(df, attribute, value, casualty_name):
    description_template = df.loc[(df['attribute'] == attribute) & df['text_value'].isna(), 'description'].values[0]
    if df.loc[df['attribute'] == attribute, 'type'].values[0] == 'categorical-continuous':
        return description_template.replace("#name#", casualty_name).replace("$value$", str(value))
    else:
        return f"{description_template} {value}"

def get_multicategorical_descriptions(df, attribute, value):
    filtered_df = df[(df['attribute'] == attribute) & (df['text_value'] == value)]
    return filtered_df['description'].tolist() if not filtered_df.empty else []

def generate_first_description(new_instance, most_similar_instance, action_new_instance, action_most_similar):
    if 'treatment' in new_instance and new_instance['treatment']:
        treatment_new_instance = new_instance['treatment']
        treatment_most_similar_instance = most_similar_instance.get('treatment')
        return select(action_new_instance, action_most_similar, treatment_new_instance, treatment_most_similar_instance)
    elif action_new_instance == 'tag_character':
        params = {
            "casualty": most_similar_instance["casualty"],
            "category": new_instance["category"],
            "category_most_similar": most_similar_instance["category"]
        }
        return select(action_new_instance, action_most_similar, params=params)
    else:
        return select(action_new_instance, action_most_similar)

def add_and_to_last_comma(final_description):
    last_comma_index = final_description.rfind(',')
    if last_comma_index != -1:
        return final_description[:last_comma_index + 1] + ' and' + final_description[last_comma_index + 1:]
    else:
        return final_description