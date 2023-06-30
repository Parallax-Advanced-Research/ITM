import csv
import json

class Worker_Agent:
    def __init__(self, id, quality, productivity, svq):
        self.reputation = 0.5
        self.id = id
        self.p_high_quality = quality
        self.max_productivity = productivity
        self.svq = svq
        #self.current_tasks = []

    def __repr__(self):
        return repr(self.id + ":" + self.p_high_quality + ":" + self.max_productivity + ":" + self.svq)

    @staticmethod
    def read_csv():
        workers = []
        with open('Agile_Manager/Worker Agents.csv') as csv_file:   # ID	Value	Difficulty	Effort Required	Deadline
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    print(f'Column names are {", ".join(row)}')
                    line_count += 1
                else:
                    print(f'\t{row[0]} {row[1]} {row[2]} {row[3]}')
                    t = Worker_Agent(row[0],row[1],row[2],row[3])
                    workers.append(t)
                    line_count += 1
            print(f'Processed {line_count} lines.')
        print("workers: ",workers)
        return workers

    def to_json(self):
        return json.dumps(self.__dict__)

    @staticmethod
    def list_to_json_file(l):
        with open("Agile_Manager/Worker Agents.json", "w") as file:
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
        workers = []
        with open('Agile_Manager/Worker Agents.json') as file:
            parsed_json1 = json.load(file)
            for j in parsed_json1:
                workers.append(j)
        return workers

#    def write_csv(self):

    @staticmethod
    def test():
        workers = Worker_Agent.read_csv()
        for t in workers:
            print(t.to_json())
        Worker_Agent.list_to_json_file(workers)
        print("Worker Agents")
        print(Worker_Agent.from_json_file())
