# from app.importers.importer import Importer
import yaml
from app.case.models import Case
from app.scenario.models import Scenario, Threat, Casualty, Vitals, Supply, Environment
from app.probe.models import Probe, ProbeOption
import os


class YAMLImporter:
    def __init__(self):
        pass

    def import_case(self, file_path, casebase_id):
        data = yaml.load(open(file_path), Loader=yaml.FullLoader)
        case_name = ""
        filename = ""
        if file_path is not None:
            filename = file_path.split("/")[-1].split(".")[0]
        if "name" in data:
            case_name = data[
                "name"
            ]  # human-readable scenario name, not necessarily unique
        elif filename != "":
            case_name = self.file_path.split("/")[-1].split(".")[0]
        else:
            case_name = "Untitled"
        external_id = None
        if "id" in data:
            external_id = data["id"]  # globally unique id

        scenario_casualties = []

        if "state" in data:
            scenario_state = data["state"]
            scenario_description = scenario_state["unstructured"]
            scenario_mission_description = scenario_state["mission"]["unstructured"]
            scenario_mission_type = scenario_state["mission"]["mission_type"]

            scenario = Scenario(
                created_by="import" if external_id is None else "import-" + external_id,
                description=scenario_description,
                mission_description=scenario_mission_description,
                mission_type=scenario_mission_type,
            )

            if "environment" in scenario_state:
                environment = Environment(
                    aid_delay=scenario_state["environment"]["aidDelay"],
                    unstructured=scenario_state["environment"]["unstructured"],
                    created_by="import",
                )
                scenario.environment.append(environment)

            if "threat_state" in scenario_state:
                scenario_threat_state = scenario_state["threat_state"]
                threat_state_description = scenario_threat_state["unstructured"]
                scenario.threat_state_description = threat_state_description
                scenario_threats = (
                    scenario_state["threats"] if "threats" in scenario_state else []
                )
                for threat in scenario_threats:
                    threat_type = threat["type"]
                    threat_severity = threat["severity"]
                    threat = Threat(
                        threat_type=threat_type,
                        threat_severity=threat_severity,
                    )
                    scenario.threats.append(threat)

            if (
                "casualties" in scenario_state
                and scenario_state["casualties"] is not None
            ):
                scenario_casualties = scenario_state["casualties"]

            if "supplies" in scenario_state:
                scenario_supplies = scenario_state["supplies"]
                if scenario_supplies is not None:
                    for supply in scenario_supplies:
                        supply_type = supply["type"]
                        supply_quantity = supply["quantity"]
                        supply = Supply(
                            supply_type=supply_type,
                            supply_quantity=supply_quantity,
                        )
                        scenario.supplies.append(supply)

            if "elapsed_time" in scenario_state:
                scenario_elapsed_time = scenario_state["elapsed_time"]
                scenario.elapsed_time = scenario_elapsed_time

        if "probes" in data:
            scenario_probes = data["probes"]

        case = Case(
            external_id=external_id,
            name=case_name,
            casebase_id=casebase_id,
            created_by="import" if external_id is None else "import-" + external_id,
        )

        casualty_relationship_type = "NONE"
        casualty_rank = ""
        for casualty in scenario_casualties:
            casualty_age = casualty["demographics"]["age"]
            casualty_sex = casualty["demographics"]["sex"]
            if "rank" in casualty["demographics"]:
                casualty_rank = casualty["demographics"]["rank"]
            if "relationship" in casualty:
                casualty_relationship_type = casualty["relationship"]["type"]
            new_casualty = Casualty(
                name=casualty["id"],
                description=casualty["unstructured"],
                age=casualty_age,
                sex=casualty_sex,
                rank=casualty_rank,
                relationship_type=casualty_relationship_type,
            )
            heart_rate = casualty["vitals"]["hrpmin"]
            blood_pressure = casualty["vitals"]["mmHg"]
            if "Spo2" in casualty["vitals"]:
                oxygen_saturation = casualty["vitals"]["Spo2"]
            elif "SpO2%" in casualty["vitals"]:
                oxygen_saturation = casualty["vitals"]["SpO2%"]
            respiratory_rate = casualty["vitals"]["RR"]
            pain = casualty["vitals"]["Pain"]

            vitals = Vitals(
                heart_rate=heart_rate,
                blood_pressure=blood_pressure,
                oxygen_saturation=oxygen_saturation,
                respiratory_rate=respiratory_rate,
                pain=pain,
            )
            new_casualty.vitals.append(vitals)
            scenario.casualties.append(new_casualty)

        for scenario_probe in scenario_probes:
            probe_type = scenario_probe["type"]
            probe_id = scenario_probe["id"]
            probe_prompt = scenario_probe["prompt"]
            probe_state = ""
            if "state" in scenario_probe:
                if "unstructured" in scenario_probe["state"]:
                    probe_state = scenario_probe["state"]["unstructured"]

            probe = Probe(
                type=probe_type,
                prompt=probe_prompt,
                state=probe_state,
                probe_id=probe_id,
                created_by="import",
            )

            options = []
            if "options" in scenario_probe:
                for probe_option in scenario_probe["options"]:
                    probe_option_id = probe_option["id"]
                    probe_option_value = probe_option["value"]
                    option = ProbeOption(
                        choice_id=probe_option_id,
                        value=probe_option_value,
                        created_by="import",
                    )
                    options.append(option)
            probe.options = options

            scenario.probes.append(probe)

        scenario.save()
        case.scenarios.append(scenario)
        case.save()

    def import_cases(self, dir_path, casebase_id=1):
        for file in sorted(os.listdir(dir_path)):
            if file.endswith(".yaml") and file.startswith("MVP2"):
                print(file)
                try:
                    self.import_case(dir_path + "/" + file, casebase_id)
                except Exception as e:
                    print(e)
                    print("Failed to import " + file)
                    continue
