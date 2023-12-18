class Importer(object):
    def __init__(self, file_path):
        self.file_path = file_path

    def import_data(self):
        with open(self.file_path, "r") as f:
            return self.load(f.read())
