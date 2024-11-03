import os

from components import Assessor

from  triage.competence_assessor import CompetenceAssessor


dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'triage', 'data')
#file_paths = [os.path.join(dir_path, f) for f in os.listdir(dir_path)]

tag_file = os.path.join(dir_path, 'ta3-ph1','phase1-adept-train-IO1v2.yaml') # to test tagging characters


CompetenceAssessor = CompetenceAssessor(Assessor) # there will be assessors for assessing, tagging, treating, leaving
CompetenceAssessor.assess(dir_path)

print("test file: ", tag_file)

