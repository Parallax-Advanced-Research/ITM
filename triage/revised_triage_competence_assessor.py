from components import Assessor
from domain.internal import TADProbe, Decision, Action
from domain.ta3 import Casualty, Injury
from domain.enum import ActionTypeEnum, SupplyTypeEnum, TagEnum, InjuryTypeEnum, InjurySeverityEnum, \
                        MentalStatusEnum, HeartRateEnum, BloodOxygenEnum, AvpuLevelEnum, \
                        BreathingLevelEnum, ParamEnum

PAINMED_SUPPLIES = [SupplyTypeEnum.PAIN_MEDICATIONS, SupplyTypeEnum.FENTANYL_LOLLIPOP]
CHECK_ACTION_TYPES = [ActionTypeEnum.CHECK_ALL_VITALS, ActionTypeEnum.CHECK_BLOOD_OXYGEN, 
                      ActionTypeEnum.CHECK_PULSE, ActionTypeEnum.CHECK_RESPIRATION, 
                      ActionTypeEnum.SITREP]

class TriageCompetenceAssessor(Assessor):
    def assess(self, probe: TADProbe) -> dict[Decision, float]:
        treatment_available = sum([1 for dec in probe.decisions if is_treatment_action(dec.value)])
        painmeds_available = sum([1 for dec in probe.decisions if is_painmed_action(dec.value)])
        check_available = sum([1 for dec in probe.decisions if is_check_action(dec.value)])
        
        ret_assessments = {}
        neediest_tag = get_neediest_tag(probe)
        
        for dec in probe.decisions:
            dec_key = str(dec.value)
            action_type = dec.value.name
            casualty = get_target_patient(probe, dec)

            if action_type == ActionTypeEnum.END_SCENE:
                ret_assessments[dec_key] = self.check_end_scene_decision(dec, treatment_available, check_available, painmeds_available)
            elif action_type == ActionTypeEnum.APPLY_TREATMENT:
                ret_assessments[dec_key] = self.assess_treatment_decision(dec, casualty, neediest_tag)
            elif action_type == ActionTypeEnum.MOVE_TO_EVAC:
                ret_assessments[dec_key] = self.assess_evac_decision(dec, casualty)
            elif action_type == ActionTypeEnum.TAG_CHARACTER:
                ret_assessments[dec_key] = self.assess_tag_decision(dec, casualty)
            else:
                ret_assessments[dec_key] = 1  # Default score for neutral or unclear decisions

        return ret_assessments

    def check_end_scene_decision(self, decision, treatment_available, check_available, painmeds_available):
        """Assess if ending the scene is premature given available actions."""
        if treatment_available > 0:
            return 0  # Ending the scene prematurely when treatment is still available
        elif check_available > 0:
            return 0.2
        elif painmeds_available > 0:
            return 0.5
        else:
            return 1

    def assess_treatment_decision(self, decision, casualty, neediest_tag):
        """Assess if a treatment decision aligns with TCCC priorities."""

        # Massive hemorrhage must be treated first
        if casualty:
            # Check if tourniquet is being applied to an inappropriate body part
            if decision.value.name == ActionTypeEnum.APPLY_TOURNIQUET:
                if any(injury.name == InjuryTypeEnum.AMPUTATION for injury in casualty.injuries):
                    # Only allow tourniquet on limbs with bleeding
                    if not self.is_limb_injury(casualty.injuries):
                        return 0  # Critical error: tourniquet applied to inappropriate body part

                elif decision.value.name != ActionTypeEnum.APPLY_TOURNIQUET:
                    return 0  # Tourniquet missed for amputation injury with bleeding

            # Airway management for unconscious casualties
            if casualty.vitals.avpu == AvpuLevelEnum.UNRESPONSIVE:
                if decision.value.name != ActionTypeEnum.APPLY_AIRWAY:
                    return 0.1  # Failed to apply airway intervention for unresponsive patient

            # Proper prioritization for respiratory distress
            if casualty.vitals.breathing == BreathingLevelEnum.NONE:
                if decision.value.name not in [ActionTypeEnum.APPLY_CHEST_SEAL, ActionTypeEnum.APPLY_NEEDLE_DECOMPRESSION]:
                    return 0.1  # Failed to address breathing emergency

        return 1  # Correct or less critical decisions

    def assess_evac_decision(self, decision, casualty):
        """Evaluate if evacuation prioritizes the correct casualties."""
        # Expectant casualties should not be prioritized for evacuation over Immediate casualties
        cur_tag = max(get_tags(casualty), key=neediness)
        if cur_tag == TagEnum.EXPECTANT and casualty:
            return 0.1  # Incorrect prioritization for evacuation
        return 1

    def assess_tag_decision(self, decision, casualty):
        """Assess the correctness of triage tagging."""
        correct_tag = determine_tag(casualty)[0] if casualty else TagEnum.MINIMAL
        given_tag = decision.value.params[ParamEnum.CATEGORY]
        if given_tag != correct_tag:
            return 0.5 if given_tag in determine_tag(casualty) else 0.2
        return 1

    def is_limb_injury(self, injuries):
        """Check if any injuries are located on limbs (appropriate for tourniquet use)."""
        for injury in injuries:
            if injury.location in ["ARM", "LEG"]:  # Assuming ARM and LEG are locations in InjuryTypeEnum
                return True
        return False

# Utility functions from previous version
def get_neediest_tag(probe: TADProbe):
    # ... (existing logic)

def get_target_patient(probe: TADProbe, dec: Decision):
    # ... (existing logic)

def get_tags(patient: Casualty) -> str:
    # ... (existing logic)
    
def determine_tag(patient: Casualty) -> list[str]:
    # ... (existing logic)

# Additional utility functions...
