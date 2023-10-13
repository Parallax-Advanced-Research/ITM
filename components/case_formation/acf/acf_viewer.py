import sys

sys.path.append(".")
from components.case_formation.acf.app import app

if __name__ == "__main__":
    app.run(debug=True)
