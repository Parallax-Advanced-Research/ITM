import sys

sys.path.append(".")
from components.case_formation.acf.app import app

app.run(debug=True)
