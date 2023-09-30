from typing import Any, Dict, List, Optional, Union
import csv

class CSVReader:
    def __init__(self, input_file) -> None:
        self._csv_file_path: str = input_file  
        self._csv_rows: list[dict] = []        
    
   
    def read_csv_multi(self):
        csv_cases: list[dict] = []
        with open(self._csv_file_path, "r") as f:
            reader = csv.reader(f, delimiter=",")
            headers: list[str] = next(reader)
            # the first header had some special characters in it
            headers[0] = "Case_#"
            
            for i in range(len(headers)):
                headers[i] = headers[i].strip().replace("'", "").replace('"', "")

            kdmas = headers[
                headers.index("mission-Ave") : headers.index("timeurg-M-A") + 1
            ]
            
            for line in reader:
                case = {}
                for i, entry in enumerate(line):
                    case[headers[i]] = entry.strip().replace("'", "").replace('"', "")                
                # Clean KDMAs
                _kdmas = self._replace(case, kdmas, "kdmas")
                for kdma in list(_kdmas.keys()):
                    if kdma.endswith("-Ave"):
                        _kdmas[kdma.split("-")[0]] = _kdmas[kdma]
                    del _kdmas[kdma]
                # Skip any entires that don't have KDMA values
                if list(_kdmas.values())[0].lower() == "na":
                    continue

                # Clean supplies
                sup_type = case.pop("Supplies: type")
                sup_quant = case.pop("Supplies: quantity")
                case["supplies"] = {sup_type: sup_quant}
            
                # Clean action
                case["action"] = {
                    "type": case.pop("Action type"),
                    "params": [
                        param.strip() for param in case.pop("Action").split(",")
                    ][1:],
                }

                # the casualties are 5 groups of 19 columns starting from column 21
                casualty_data = []
                for i in range(5):
                    casualty_group = {}
                    
                    for j in range(19):
                        casualty_group[headers[21 + i * 19 + j]] = line[21 + i * 19 + j]
                    
                    # Clean casualty data                        
                    cas_id = casualty_group.pop("Casualty_id")    
                    cas_name = casualty_group.pop("casualty name")                        
                    cas_unstructured = casualty_group.pop("Casualty unstructured")
                    cas_relation = casualty_group.pop("casualty_relationship")
                    casualty_group["casualty"] = {
                        "id": cas_id,
                        "name": cas_name,
                        "unstructured": cas_unstructured,
                        "relation": cas_relation,
                    }
                    
                    # Clean demographics
                    demo_age = casualty_group.pop("age")
                    demo_sex = casualty_group.pop("IndividualSex")
                    demo_rank = casualty_group.pop("IndividualRank")
                    casualty_group["demographics"] = {
                        "age": demo_age,
                        "sex" : demo_sex,
                        "rank" : demo_rank,
                    }
                    
                    # Clean Injury
                    injury_name = casualty_group.pop("Injury name")
                    injury_location = casualty_group.pop("Injury location")
                    injury_severity = casualty_group.pop("severity")
                    casualty_group["injury"] = {
                        "name": injury_name,
                        "location": injury_location,
                        "severity": injury_severity,
                    }
                    
                    # Clean vitals
                    casualty_group["vitals"] = {
                        "responsive": casualty_group.pop("vitals:responsive"),
                        "breathing": casualty_group.pop("vitals:breathing"),
                        "hrpm": casualty_group.pop("hrpmin"),
                        "mmhg": casualty_group.pop("mmHg"),
                        "rr": casualty_group.pop("RR"),
                        "spo2": casualty_group.pop("Spo2"),
                        "pain": casualty_group.pop("Pain"),
                        }                
                case["casualties"] = casualty_data

            
            
                csv_cases.append(case)
                
    @staticmethod
    def _replace(case: dict, headers: list[str], name_: str) -> dict[str, any]:
        sub_dict = {}
        for header in headers:
            sub_dict[header] = case[header]
            del case[header]
        case[name_] = sub_dict
        return sub_dict
csv_reader = CSVReader("data/sept/case_base_multicas.csv")
csv_reader.read_csv_multi()