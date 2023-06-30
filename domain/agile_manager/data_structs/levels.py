import csv
import json

class Level:
    def __init__(self, level, svq, roundsnum, tasksnum, product):  # Level	Speed vs. Quality Trade-off (SvQ)	No. of Rounds	Tasks per Round	Average Worker Agent Productivity Output Rate
        self.level = level
        self.svq = svq
        self.roundsnum = roundsnum
        self.tasksnum = tasksnum
        self.product = product
        #self.current_tasks = []

    def __repr__(self):
        return repr(self.level + ":" + self.svq + ":" + self.roundsnum + ":" + self.tasksnum + ":" + self.product)

    @staticmethod
    def read_csv():
        levels = []
        with open('Agile_Manager/Game Levels.csv') as csv_file:   # ID	Value	Difficulty	Effort Required	Deadline
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    print(f'Column names are {", ".join(row)}')
                    line_count += 1
                else:
                    print(f'\t{row[0]} {row[1]} {row[2]} {row[3]} {row[4]}')
                    t = Level(row[0],row[1],row[2],row[3],row[4])
                    levels.append(t)
                    line_count += 1
            print(f'Processed {line_count} lines.')
        print("workers: ",levels)
        return levels

    def to_json(self):
        return json.dumps(self.__dict__)

    @staticmethod
    def list_to_json_file(l):
        with open("Agile_Manager/Game Levels.json", "w") as file:
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
        levels = []
        with open('Agile_Manager/Game Levels.json') as file:
            parsed_json1 = json.load(file)
            for j in parsed_json1:
                levels.append(j)
        return levels

#    def write_csv(self):

    @staticmethod
    def test():
        levels = Level.read_csv()
        for t in levels:
            print(t.to_json())
        Level.list_to_json_file(levels)
        print("Levels")
        print(Level.from_json_file())
