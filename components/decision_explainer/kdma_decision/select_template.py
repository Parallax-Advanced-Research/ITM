def select(action_new_instance, action_most_similar_instance, treatment_new_instance=None, treatment_most_similar_instance=None, params=None):
    action = action_new_instance.lower()
    action_most_similar_instance = action_most_similar_instance.lower()
    template = ''
    if action == "apply_treatment":
        action_str = action.replace('_', ' ')
        action_most_similar_instance_str = action_most_similar_instance.replace('_', ' ')

        treatment_new_instance = treatment_new_instance.lower()
        treatment_new_instance = treatment_new_instance.replace('_', ' ')

        treatment_most_similar_instance = treatment_most_similar_instance.lower()
        treatment_most_similar_instance = treatment_most_similar_instance.replace('_', ' ')

        template = "I selected " + action_str + " with " + treatment_new_instance + " because I was reminded of a similar previous case where a similar decision maker decided to " + action_most_similar_instance_str + " with " + \
                             treatment_most_similar_instance
    elif action == "sitrep":
        if action_most_similar_instance == 'sitrep':
            action_most_similar_instance = 'situation report'
        template = "I decided to submit a situation report to provide an update on the current status because I was reminded of a previous case where a similar decision maker decided to submit " + action_most_similar_instance
    elif action == "tag_character":
        casualty_name = params['casualty'].lower() if 'casualty' in params and params['casualty'] else 'unknown'
        category = params['category'].lower() if 'category' in params and params['category'] else 'Unknown'
        category_most_similar = params['category_most_similar'].lower() if 'category_most_similar' in params and params['category_most_similar'] else 'Unknown'
        template = "I selected to tag "+casualty_name+" as "+category+" because I was reminded of a previous case where a similar decision maker decided to tag casualty as "+category_most_similar
    elif action == "check_all_vitals" or action == "check_blood_oxygen" or action == "check_pulse" or action == "check_respiration":
        action_str = action.replace('_', ' ')
        action_most_similar_instance_str = action_most_similar_instance.replace('_', ' ')
        template = "I selected to " + action_str + " because I was reminded of a previous case where a similar decision maker decided to " + action_most_similar_instance_str
    else:
        print("Unknown action")
    return template
