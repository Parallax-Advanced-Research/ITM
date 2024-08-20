import pandas as pd
import re
from .select_template import select

def convert_to_percentage(match):
    value = float(match.group(0)) * 100
    return f"{value:.0f}%"

def generate_explanation_text(new_instance, most_similar_instance, action_new_instance, action_most_similar):

    pattern = r'\b0\.\d+'

    df = pd.read_csv("components/decision_explainer/kdma_decision/case_base.csv")

    descriptions = []

    for attributeName, value in most_similar_instance.items():
        if '.' in attributeName and attributeName != 'HRA Strategy.time-resources.take-the-best':
            attribute, casualty_name = attributeName.split('.', 1)
        else:
            attribute = attributeName
            casualty_name = 'Unknown'
        attribute_types = df.loc[df['attribute'] == attribute, 'type']
        # attribute_type = attribute_types.values[0]

        if attribute_types.empty:
            attribute_type = None
        else:
            attribute_type = attribute_types.values[0]

        if attribute_type is None:
            continue
        else:
            if attribute_type == 'boolean':
                value = value.lower() == 'true'
                filtered_df = df[(df['attribute'] == attribute) & (
                        df['text_value'] == value)]
                if not filtered_df.empty:
                    descriptions.extend(filtered_df['description'].tolist())
            elif attribute_type == 'continuous':
                description_template = \
                    df.loc[(df['attribute'] == attribute) & df['text_value'].isna(), 'description'].values[0]
                description = f"{description_template} {value}"
                descriptions.append(description)
            elif attribute_type == 'categorical':
                if attribute != "treatment":
                    description_template = \
                        df.loc[(df['attribute'] == attribute) & df['text_value'].isna(), 'description'].values[0]
                    description = f"{description_template} {value}"
                    descriptions.append(description)
            elif attribute_type == 'categorical-continuous':
                description_template = \
                    df.loc[(df['attribute'] == attribute) & df['text_value'].isna(), 'description'].values[0]
                description = description_template.replace("#name#", casualty_name).replace("$value$", str(value))
                descriptions.append(description)
            elif attribute_type == 'multicategorical':
                filtered_df = df[(df['attribute'] == attribute) & (
                        df['text_value'] == value)]
                if not filtered_df.empty:
                    descriptions.extend(filtered_df['description'].tolist())
            elif attribute_type == 'binary':
                filtered_df = df[(df['attribute'] == attribute) & (
                        df['text_value'] == value)]
                if not filtered_df.empty:
                    descriptions.extend(filtered_df['description'].tolist())

    joined_descriptions = ", ".join(descriptions)

    if joined_descriptions:
        if 'treatment' in new_instance and new_instance['treatment']:
            treatment_new_instance = new_instance['treatment']
            if 'treatment' in most_similar_instance and most_similar_instance['treatment']:
                treatment_most_similar_instance = most_similar_instance['treatment']
            else:
                treatment_most_similar_instance = None
            first_description = select(action_new_instance, action_most_similar, treatment_new_instance,
                                       treatment_most_similar_instance)
        elif action_new_instance == 'tag_character':
            params = {"casualty": most_similar_instance["casualty"], "category": new_instance["category"],
                      "category_most_similar": most_similar_instance["category"]}
            first_description = select(action_new_instance, action_most_similar, params)
        else:  # move-to_evac, direct_mobile_characters, and others
            first_description = select(action_new_instance, action_most_similar)

        final_description = first_description + ". In a prior case where " + joined_descriptions + "."
        last_comma_index = final_description.rfind(',')

        if last_comma_index != -1:
            complete_desc = final_description[:last_comma_index + 1] + ' and' + final_description[last_comma_index + 1:]
        else:
            complete_desc = final_description
    else:
        complete_desc = "No matching descriptions found."

    complete_desc = re.sub(pattern, convert_to_percentage, complete_desc)
    return complete_desc
