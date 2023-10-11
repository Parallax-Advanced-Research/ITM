import json
import logging

from runner import TA3Driver, TA3Client
from util import logger, dict_difference


def main():
    # NOTE: TA3 server must be running for this to work.
    #  Ensure that `python -m swagger_server` has been run in the ta3 server directory. See Running-TAD.md

    # Initialize the drivers
    #  NOTE: Update TA3 Driver with any updated components you want used (e.g., analyzers)
    driver = TA3Driver()
    client = TA3Client()
    sid = client.start_session(f'TAD-Manual')

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
                difference = dict_difference(probe.state, new_probe.state, {'id', 'type'})
                logger.debug(f"-State Changes: {json.dumps(difference, indent=4)}")
            probe = new_probe


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    main()
