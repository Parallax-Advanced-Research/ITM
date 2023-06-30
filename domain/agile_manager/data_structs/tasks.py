import csv
import json

class Task:
    def __init__(self, id, v, d,e):
        self.id = id
        self.value = v
        self.difficulty = d
        self.effort = e

    def __repr__(self):
        return repr(self.id + ":" + self.value + ":" + self.difficulty + ":" + self.effort)

    @staticmethod
    def read_csv():
        tasks = []
        with open('Agile_Manager/Tasks.csv') as csv_file:   # ID	Value	Difficulty	Effort Required	Deadline
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    print(f'Column names are {", ".join(row)}')
                    line_count += 1
                else:
                    print(f'\t{row[0]} {row[1]} {row[2]} {row[3]}')
                    t = Task(row[0],row[1],row[2],row[3])
                    tasks.append(t)
                    line_count += 1
            print(f'Processed {line_count} lines.')
        print("tasks: ",tasks)
        return tasks

    def to_json(self):
        return json.dumps(self.__dict__)

    @staticmethod
    def list_to_json_file(l):
        with open("Agile_Manager/Tasks.json", "w") as file:
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
        tasks = []
        with open('Agile_Manager/Tasks.json') as file:
            parsed_json1 = json.load(file)
            for j in parsed_json1:
                tasks.append(j)
        return tasks

#    def write_csv(self):

    @staticmethod
    def test():
        tasks = Task.read_csv()
        for t in tasks:
            print(t.to_json())
        Task.list_to_json_file(tasks)
        print("Tasks")
        print(Task.from_json_file())
