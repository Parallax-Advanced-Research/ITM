import uuid
import csv
import json

class Probe:
    def __init__(self, sess, round, game_lvl, user, svq, num_tasks, was):
        self.id = str(uuid.uuid4())
        self.session = sess
        self.round = round
        self.game_lvl = game_lvl
        self.user = user
        self.svq = svq
        self.num_tasks = num_tasks
        self.worker_agents = was

    def get_id(self):
        return self.id

    def add_task(self, worker_id, tsk):
        if worker_id in self.worker_agents:
            self.worker_agents[worker_id].append(tsk)
        else:
            self.worker_agents[worker_id] = [tsk]

    def get_tasks(self):
        return self.worker_agents

    def __repr__(self):
        return repr(self.id + ":" + self.session + ":" + repr(self.round) + ":" +
                    repr(self.game_lvl) + ":" + repr(self.user) + ":" + repr(self.svq) + ":" + repr(self.num_tasks) + ":" +
                    str(self.worker_agents))

    @staticmethod
    def read_csv():
        decisions = []
        with open('Agile_Manager/Decisions.csv') as csv_file:   # ID	Value	Difficulty	Effort Required	Deadline
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    print(f'Column names are {", ".join(row)}')
                    line_count += 1
                else:
                    print(f'\t{row[0]} {row[1]} {row[2]} {row[3]} {row[4]} {row[5]} {row[6]}')
                    queue = row[6].split(";")
                    t = Probe(row[0],row[1],row[2],row[3],row[4],row[5],queue)
                    decisions.append(t)
                    line_count += 1
            print(f'Processed {line_count} lines.')
        print("decisions: ",decisions)
        return decisions

    def to_json(self):
        return json.dumps(self.__dict__)

    @staticmethod
    def list_to_json_file(l):
        with open("Agile_Manager/Decisions.json", "w") as file:
            file.write('[')
            initial = True;
            for t in l:
                if initial:
                    initial = False
                else:
                    file.write(',')
                file.write(t.to_json())
            file.write(']')

    @staticmethod
    def from_json_file():
        decisions = []
        with open('Agile_Manager/Decisions.json') as file:
            parsed_json1 = json.load(file)
            for j in parsed_json1:
                decisions.append(j)
        return decisions

#    def write_csv(self):

    @staticmethod
    def test():
        probes = Probe.read_csv()
        for t in probes:
            print(t.to_json())
        Probe.list_to_json_file(probes)
        print("Probes")
        print(Probe.from_json_file())

