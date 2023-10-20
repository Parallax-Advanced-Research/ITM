# from app.importers.importer import Importer
import yaml
from app.case.models import Case, CaseBase
from app.scenario.models import Scenario, Threat, Casualty, Vitals, Supply
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
            case_name = data["name"]
        elif filename != "":
            case_name = self.file_path.split("/")[-1].split(".")[0]
        else:
            case_name = "Untitled"
        external_id = None
        if "id" in data:
            external_id = data["id"]

        scenario_state = None
        scenario_description = None
        scenario_mission_description = None
        scenario_mission_type = None
        scenario_environment = None
        scenario_threat_state = None
        scenario_casualties = []
        scenario_probes = []

        if "state" in data:
            scenario_state = data["state"]
            scenario_description = scenario_state["unstructured"]
            scenario_mission_description = scenario_state["mission"]["unstructured"]
            scenario_mission_type = scenario_state["mission"]["mission_type"]

            if "casualties" in scenario_state:
                scenario_casualties = scenario_state["casualties"]

        if "probes" in data:
            scenario_probes = data["probes"]

        case = Case(
            external_id=external_id,
            name=case_name,
            casebase_id=casebase_id,
            created_by="import" if external_id is None else "import-" + external_id,
        )
        scenario = Scenario(
            created_by="import" if external_id is None else "import-" + external_id,
            description=scenario_description,
            mission_description=scenario_mission_description,
            mission_type=scenario_mission_type,
        )
        for casualty in scenario_casualties:
            casualty_age = casualty["demographics"]["age"]
            casualty_sex = casualty["demographics"]["sex"]
            casualty_rank = casualty["demographics"]["rank"]
            casualty = Casualty(
                name=casualty["id"],
                description=casualty["unstructured"],
                age=casualty_age,
                sex=casualty_sex,
                rank=casualty_rank,
            )

            scenario.casualties.append(casualty)

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
            )

            options = []
            if "options" in scenario_probe:
                for probe_option in scenario_probe["options"]:
                    probe_option_id = probe_option["id"]
                    probe_option_value = probe_option["value"]
                    option = ProbeOption(
                        choice_id=probe_option_id,
                        value=probe_option_value,
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
