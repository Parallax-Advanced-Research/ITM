import yaml
import glob
import argparse

from components.decision_assessor.competence.tccc_competence_assessor import TCCCCompetenceAssessor
from domain.internal import TADProbe, KDMA, KDMAs, make_new_action_decision
from domain.ta3 import TA3State
from components.elaborator.default.ta3_elaborator import TA3Elaborator
from util import logger

def test_actions(scenario_file, interactive):
    logger.info("\n\nTesting actions in " + scenario_file + ".")
    elaborator: TA3Elaborator = TA3Elaborator(False)

    with open(scenario_file, "r") as f:
        file_contents = f.read()
    scenario_dict = yaml.load(file_contents, yaml.Loader)
    state_dict = dict(scenario_dict['state'])

    st = TA3State.from_dict(state_dict)

    for scene_dict in scenario_dict['scenes']:
        logger.info("\n\nLooking into scene " + scene_dict['id'] + ".")

        if 'state' in scene_dict:
            # Update the state with scene-specific data
            if scene_dict.get('persist_characters', False) and 'characters' in scene_dict['state']:
                new_characters = list(state_dict.get('characters', []))
                for revised_character in scene_dict['state'].get('characters', []):
                    new_characters = [old_char for old_char in new_characters if old_char['id'] != revised_character['id']]
                    new_characters.append(revised_character)
                scene_dict = scene_dict.copy()
                scene_dict['state']['characters'] = new_characters
            state_dict.update(scene_dict['state'])
            st = TA3State.from_dict(state_dict)
            st.orig_state = state_dict

        # Create decisions for the scene
        decisions = []
        for action_map_dict in scene_dict['action_mapping']:
            kdmas = None
            if 'kdma_association' in action_map_dict:
                kdmas = KDMAs([KDMA(k, v) for k, v in action_map_dict['kdma_association'].items()])
            params = dict()
            if 'parameters' in action_map_dict:
                params.update(action_map_dict['parameters'])
            if 'character_id' in action_map_dict:
                params.update({'casualty': action_map_dict['character_id']})
            decisions.append(make_new_action_decision(action_map_dict['action_id'], 
                             action_map_dict['action_type'], params, kdmas, 
                             action_map_dict.get('intent_action', False)))

        # Create a probe for the scene
        probe_config = scene_dict.get('probe_config', dict())
        if isinstance(probe_config, list):
            probe_config = probe_config[0]
        probe = TADProbe(scene_dict['id'], st, probe_config.get('description', 'What next?'), state_dict['environment'], decisions)
        probe.state.actions_performed = [d.value for d in decisions if d.value.name != "MESSAGE"][:1]

        # Elaborate and assess decisions
        elaborated_decisions = elaborator.elaborate(None, probe, verbose=True)

        # Log the final decisions and competence scores
        logger.info(f"Ranked adjusted assessments for {scene_dict['id']}:")
        for decision in elaborated_decisions:
            competence_score = TCCCCompetenceAssessor().assess(probe)[str(decision.value)]
            logger.info(f"  Decision: {decision.value} -> Competence: {competence_score}")

        if interactive:
            input("Press Enter to continue to the next scene...")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_filenames", metavar="CASEBASE", type=str, nargs='+',
                        help="List of csv files with case data")
    parser.add_argument("--interactive", action="store_true",
                        help="Process one scene at a time, move to the next scene if Enter is pressed")
    args = parser.parse_args()
    for fileglob in args.input_filenames:
        for fname in glob.glob(fileglob):
            test_actions(fname, args.interactive)
            
if __name__ == '__main__':
    main()
