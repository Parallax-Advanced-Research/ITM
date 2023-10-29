import json
from app.probe.models import Probe, ProbeOption, ProbeResponse, KDMA, Alignment
from app import db


class SessionImporter:
    def import_data(self):
        data = {}
        with open("data/mvp2_input/MVP2_synthetic_data_150.json") as f:
            data = json.load(f)

        messages = data["messages"]

        for message in messages:
            session_id = message["session_id"]
            user_id = message["user_id"]

            response = message["response"]
            for item in response:
                probe_id = item["probe_id"]
                probe = Probe.query.filter_by(probe_id=probe_id).first()
                choice_id = item["choice"]
                probe_choice = ProbeOption.query.filter_by(choice_id=choice_id).first()
                if probe_choice is None:
                    print("Probe choice not found: {}".format(choice_id))
                    continue
                probe_response = ProbeResponse(
                    user_id=user_id,
                    created_by="import",
                    value=probe_choice.value,
                    probe_id=probe_id,
                    session_id=session_id,
                )
                probe_response.save()
                probe.responses.append(probe_response)
                probe.save()
                """
                if "alignment" in message:
                    session_alignment = message["alignment"]
                    alignment_score = session_alignment["score"]
                    alignment = Alignment(score=alignment_score, probe_id=probe_id)

                    if "kdma_values" in session_alignment:
                        kdma_values = session_alignment["kdma_values"]
                        for kdma_value in kdma_values:
                            kdma_name = kdma_value["kdma"]
                            kdma_value = kdma_value["value"]
                            kdma = KDMA(kdma_name=kdma_name, kdma_value=kdma_value)
                            kdma.save()
                    alignment.kdmas.append(kdma)
                  
                    alignment.save()
                    probe.alignments.append(alignment)
                    probe.save()
                """
