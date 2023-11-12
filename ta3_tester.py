import json
import logging
from copy import deepcopy

from runner import TA3Driver, TA3Client
from util import logger, dict_difference
from domain.ta3 import TA3State

def clean_state(instate: TA3State) -> TA3State:
    copy = deepcopy(instate)
    copy['actions_performed'] = list()
    for act in instate['actions_performed']:
        copy['actions_performed'] = act.to_json()
    return copy


def main():
    # NOTE: TA3 server must be running for this to work.
    #  Ensure that `python -m swagger_server` has been run in the ta3 server directory. See Running-TAD.md

    class TA3ARGS:
        def __init__(self):
            self.human = False
            self.ebd = False
            self.hra = False
            self.kedsd = False
            self.csv = True
            self.verbose = False
            self.bayes = False
            self.mc = True
            self.rollouts = 1000
            self.decision_verbose = False
            self.variant = 'aligned'
            self.training = True  # Added flag
    ta3args = TA3ARGS()

    # Initialize the drivers
    #  NOTE: Update TA3 Driver with any updated components you want used (e.g., analyzers)
    driver = TA3Driver(ta3args)
    client = TA3Client()


    # Set KDMA Trainiung to True to get kdma traimning mode from ta3 server
    sid = client.start_session(f'TAD-Manual', kdma_training=True)

    # Iterate over all TA3 sessions until complete
    #  NOTE: If a session is interrupted, the TA3 server must be restarted
    logger.info(f"Started Session-{sid}")
    while True:
        # Retrieves a scenario
        scen = client.start_scenario()
        if scen is None:
            logger.info("Session Complete!")
            break

        # Sets the scenario and KDMA information for this execution
        logger.info(f"Started Scenario-{scen.id}")
        driver.set_scenario(scen)
        driver.set_alignment_tgt(client.align_tgt)
        scen.state = clean_state(scen.state)
        logger.info(f"-Initial State: {json.dumps(scen.state, indent=4)}")

        # Gets the first probe
        probe = client.get_probe()
        while True:
            if probe is None:
                logger.info(f"Scenario Complete")
                break

            logger.info(f"Responding to probe-{probe.id}")
            # Convert the probe to internal data structures
            iprobe = driver.translate_probe(probe)
            # Elaborate the decision space (e.g., enumerate unspecified fields)
            decisions = driver.elaborate(iprobe)
            # Run Decision Analyzers on all decisions of the probe
            driver.analyze(iprobe)

            # Display actions for human selection/input
            logger.info("Actions:")
            for i, decision in enumerate(decisions):
                logger.info(f" - {i}: {decision}")
                # Display metrics for each action
                for metric_name, metric in decision.metrics.items():
                    logger.debug(f"   -Metric[{metric_name}]: {metric.value}")

            # Wait for CLI input, an integer corresponding to the action to use
            #  NOTE: Call driver.select if you want to use decision selection instead
            # human_input = int(input("Selection: "))
            selected = driver.select(iprobe)
            action = driver.respond(selected)

            # Respond to TA3
            # action = driver.respond(decisions[human_input])
            logger.debug(f"Chosen Action: {action}")

            # Get the new probe
            new_probe = client.take_action(action)
            if new_probe:
                # Calculate and show the change in the state based on this decision
                difference = dict_difference(
                    probe.state, new_probe.state, {"id", "type"}
                )
                logger.debug(f"-State Changes: {json.dumps(difference, indent=4)}")
            probe = new_probe


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    main()
