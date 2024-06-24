import json

# printing super colorful


def print_red(text):
    print('\033[1;31;48m' + text + '\033[1;37;0m')


def print_blue(text):
    print('\033[1;34;48m' + text + '\033[1;37;0m')


def print_purple(text):
    print('\033[1;35;48m' + text + '\033[1;37;0m')


def print_yellow(text):
    print('\033[1;33;48m' + text + '\033[1;37;0m')


class Decision:
    def __init__(self, action, casualty, supply, location):
        self.action = action
        self.casualty = casualty
        self.supply = supply
        self.location = location

    def __eq__(self, other):
        return (self.action == other.action and
                self.casualty == other.casualty and
                self.supply == other.supply and
                self.location == other.location)

    def __lt__(self, other):
        return (self.action < other.action and
                self.casualty < other.casualty and
                self.supply < other.supply and
                self.location < other.location)

    def __hash__(self):
        return hash((self.action, self.casualty, self.supply, self.location))

    def __str__(self):
        return f'Action: {self.action}, Casualty: {self.casualty}, Supply: {self.supply}, Location: {self.location}'

    def __repr__(self):
        return f'{{\"Action\": \"{self.action}\", \"Casualty\": \"{self.casualty}\", \"Supply\": \"{self.supply}\", \"Location\": \"{self.location}\"}}'


def load_json(file):
    with open(file) as f:
        j = json.load(f)
    return j


def convert_json(json_data):
    decisions: list[Decision] = []

    try:
        actions = json_data['actions']
    except:
        actions = json_data['Actions']

    for act in actions:
        action = act.get('action', None)
        casualty = act.get('casualty', None)
        supply = act.get('treatment', None)
        location = act.get('location', None)
        if casualty == 'None':
            casualty = None
        if supply == 'None':
            supply = None
        if location == 'None':
            location = None
        dec = Decision(action=action, casualty=casualty,
                       supply=supply, location=location)
        decisions.append(dec)
    return decisions


def compare_decisions_lists(dec_1, dec_2):
    if len(dec_1) != len(dec_2):
        print_yellow(f'Different number of actions input 1 has {len(dec_1)} and input 2 has {len(dec_2)}')
    else:
        print_yellow('Both have the same number of actions')

    # find the same stuff
    set_1 = set(dec_1)
    set_2 = set(dec_2)
    if set_1 == set_2:
        print_yellow('The 2 elaborators have the same output')
    else:
        matches = set_1 & set_2
        print_purple('the following is what is the same')
        print_purple(str(matches))
        only_1 = set_1 - set_2
        only_2 = set_2 - set_1
        print_blue('only in file 1')
        print_blue(str(only_1))
        print_red('only in file 2')
        print_red(str(only_2))


if __name__ == '__main__':
    file_1 = r'data/elab_output/MetricsEval.MD5-Desert-4_rbe.json'
    file_2 = r'data/elab_output/MetricsEval.MD5-Desert-4_gemini.json'

    json_1 = load_json(file_1)
    json_2 = load_json(file_2)

    # convert to decision in this file
    decisions_1 = convert_json(json_1)
    decisions_2 = convert_json(json_2)

    compare_decisions_lists(decisions_1, decisions_2)
