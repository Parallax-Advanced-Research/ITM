def format_action(action):
    return action.replace('_', ' ')

def select(action_new_instance, action_most_similar_instance, treatment_new_instance=None, treatment_most_similar_instance=None, params=None):
    action = action_new_instance.lower()
    action_most_similar_instance = action_most_similar_instance.lower()
    template = ''

    if action == "apply_treatment":
        template = apply_treatment_template(action, action_most_similar_instance, treatment_new_instance, treatment_most_similar_instance)
    elif action == "sitrep":
        template = sitrep_template(action_most_similar_instance)
    elif action == "tag_character":
        template = tag_character_template(params)
    elif action in {"check_all_vitals", "check_blood_oxygen", "check_pulse", "check_respiration"}:
        template = check_vitals_template(action, action_most_similar_instance)
    elif action == 'move_to_evac':
        template = "I decided to move the casualty to the designated evacuation point because I was reminded of a previous case where a similar decision maker decided to transfer a casualty to an evacuation point"
    elif action == 'direct_mobile_characters':
        template = "I decided to direct mobile characters because I was reminded of a previous case where a similar decision maker directed responsive and alert characters for a mobility check"
    else:
        template = "Unknown action"

    return template

def apply_treatment_template(action, action_most_similar_instance, treatment_new_instance, treatment_most_similar_instance):
    action_str = format_action(action)
    action_most_similar_instance_str = format_action(action_most_similar_instance)
    treatment_new_instance = format_action(treatment_new_instance.lower())

    if treatment_most_similar_instance:
        treatment_most_similar_instance = format_action(treatment_most_similar_instance.lower())
        return f"I selected {action_str} with {treatment_new_instance} because I was reminded of a similar previous case where a similar decision maker decided to {action_most_similar_instance_str} with {treatment_most_similar_instance}"
    else:
        return f"I selected {action_str} with {treatment_new_instance} because I was reminded of a similar previous case where a similar decision maker decided to {action_most_similar_instance_str}"

def sitrep_template(action_most_similar_instance):
    action_most_similar_instance = 'situation report' if action_most_similar_instance == 'sitrep' else action_most_similar_instance
    return f"I decided to submit a situation report to provide an update on the current status because I was reminded of a previous case where a similar decision maker decided to submit a {action_most_similar_instance}"

def tag_character_template(params):
    casualty_name = params.get('casualty', 'unknown').lower()
    category = params.get('category', 'unknown').lower()
    category_most_similar = params.get('category_most_similar', 'unknown').lower()
    return f"I selected to tag {casualty_name} as {category} because I was reminded of a previous case where a similar decision maker decided to tag casualty as {category_most_similar}"

def check_vitals_template(action, action_most_similar_instance):
    action_str = format_action(action)
    action_most_similar_instance_str = format_action(action_most_similar_instance)
    return f"I selected to {action_str} because I was reminded of a previous case where a similar decision maker decided to {action_most_similar_instance_str}"