from app.case.models import Case
from app.probe.models import (
    Probe,
    ProbeOption,
    ProbeResponse,
    KDMA,
    probe_response_kdma,
)
from app import db
import csv


class SoarTechResponseImporter:
    def import_data(self):
        data = {}
        with open(
            "data/st-september-2023-mvp2/scored-st-training-data-aug-2023.csv"
        ) as f:
            data = csv.DictReader(f)

            for row in data:
                probe = Probe.query.filter_by(probe_id=row["probe_id"]).first()
                if probe is None:
                    print("Probe not found: {}".format(row["probe_id"]))
                    continue

                if probe.options is None:
                    print("Probe options not found: {}".format(row["probe_id"]))
                    continue
                possible_responses = probe.options
                choices = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
                chosen_value = possible_responses[choices[row["choice"]]].value
                response = chosen_value

                mission_kdma = KDMA(
                    kdma_name="mission",
                    kdma_value=row["mission"],
                )
                mission_kdma.save()

                denial_kdma = KDMA(
                    kdma_name="denial",
                    kdma_value=row["denial"],
                )

                risktol_kdma = KDMA(
                    kdma_name="risktol",
                    kdma_value=row["risktol"],
                )

                timeurg_kdma = KDMA(
                    kdma_name="timeurg",
                    kdma_value=row["timeurg"],
                )

                probe_response = ProbeResponse(
                    user_id="test user",
                    session_id=row["session_id"],
                    created_by="import",
                    value=response,
                    probe_id=probe.probe_id,
                )
                probe_response.kdmas.append(mission_kdma)
                probe_response.kdmas.append(denial_kdma)
                probe_response.kdmas.append(risktol_kdma)
                probe_response.kdmas.append(timeurg_kdma)
                probe_response.save()
                probe.responses.append(probe_response)
                probe.save()
