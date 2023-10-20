import json
from app.case.models import Case
from app.probe.models import Probe, ProbeOption, ProbeResponse
from app import db


class ResponseImporter:
    def import_data(self):
        data = {}
        with open("data/mvp2_input/MVP2_synthetic_data_150.json") as f:
            data = json.load(f)

        messages = data["messages"]

        for message in messages:
            response = message["response"]
            user_id = message["user_id"]
            for item in response:
                scenario_id = item["scenario_id"]
                case = Case.query.filter_by(
                    external_id=scenario_id, casebase_id=1
                ).first()
                probe_id = item["probe_id"]
                probe = Probe.query.filter_by(probe_id=probe_id).first()
                choice_id = item["choice"]
                probe_choice = ProbeOption.query.filter_by(choice_id=choice_id).first()
                if probe_choice is None:
                    print("Probe choice not found: {}".format(choice_id))
                    continue
                probe_response = ProbeResponse(
                    user_id=user_id,
                    created_by="test",
                    value=probe_choice.value,
                    probe_id=probe_id,
                )
                probe_response.save()
                probe.responses.append(probe_response)
                probe.save()
                print(probe_choice)
                # get the value of the chosen option

    def delete_responses(self):
        # delete all probe responses
        ProbeResponse.query.delete()
        db.session.commit()
