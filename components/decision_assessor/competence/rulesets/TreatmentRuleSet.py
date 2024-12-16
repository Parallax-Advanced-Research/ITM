from components.decision_assessor.competence.tccc_domain_reference import InjuryLocationEnum, TreatmentsEnum
from domain.enum import BloodOxygenEnum, BreathingLevelEnum, HeartRateEnum, InjuryTypeEnum, MentalStatusEnum, SupplyTypeEnum
from domain.ta3 import Injury, Vitals


from typing import List


class TreatmentRuleSet:
    VALID_TREATMENTS = {
        # Bandage and pain management for bleeding control and discomfort.
        InjuryTypeEnum.EAR_BLEED: [
            TreatmentsEnum.PRESSURE_BANDAGE,
            TreatmentsEnum.PAIN_MEDICATIONS,
        ],
        # EpiPen to address asthma attacks and airway for severe respiratory distress.
        InjuryTypeEnum.ASTHMATIC: [
            TreatmentsEnum.EPI_PEN,
            TreatmentsEnum.NASOPHARYNGEAL_AIRWAY,
        ],
        # Standard bandage and gauze for bleeding control, plus pain relief for discomfort.
        InjuryTypeEnum.LACERATION: [
            TreatmentsEnum.PRESSURE_BANDAGE,
            TreatmentsEnum.HEMOSTATIC_GAUZE,
            TreatmentsEnum.PAIN_MEDICATIONS,
        ],
        # Bandage, gauze, and chest seal to prevent air leakage, with pain management.
        InjuryTypeEnum.PUNCTURE: [
            TreatmentsEnum.PRESSURE_BANDAGE,
            TreatmentsEnum.HEMOSTATIC_GAUZE,
            TreatmentsEnum.VENTED_CHEST_SEAL,
            TreatmentsEnum.PAIN_MEDICATIONS,
        ],
        # Gauze and bandage for wound stabilization and pain management.
        InjuryTypeEnum.SHRAPNEL: [
            TreatmentsEnum.HEMOSTATIC_GAUZE,
            TreatmentsEnum.PRESSURE_BANDAGE,
            TreatmentsEnum.PAIN_MEDICATIONS,
        ],
        # Needle decompression for collapsed lung, chest seal to prevent air leakage, and airway support.
        InjuryTypeEnum.CHEST_COLLAPSE: [
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.VENTED_CHEST_SEAL,
            TreatmentsEnum.NASOPHARYNGEAL_AIRWAY,
        ],
        # Tourniquet for major bleeding, gauze and bandage for wound care, pain relief, and blood transfusion as needed.
        InjuryTypeEnum.AMPUTATION: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.HEMOSTATIC_GAUZE,
            TreatmentsEnum.PRESSURE_BANDAGE,
            TreatmentsEnum.PAIN_MEDICATIONS,
            TreatmentsEnum.FENTANYL_LOLLIPOP,
            TreatmentsEnum.BLOOD,
        ],
        # Specialized dressing and IV fluids for hydration, pain relief, and warmth.
        InjuryTypeEnum.BURN: [
            TreatmentsEnum.BURN_DRESSING,
            TreatmentsEnum.PAIN_MEDICATIONS,
            TreatmentsEnum.IV_BAG,
            TreatmentsEnum.BLANKET,
        ],
        # Bandage and pain relief for minor cuts.
        InjuryTypeEnum.ABRASION: [
            TreatmentsEnum.PRESSURE_BANDAGE,
            TreatmentsEnum.PAIN_MEDICATIONS,
        ],
        # Splint for stabilization, plus pain relief for moderate to severe fractures.
        InjuryTypeEnum.BROKEN_BONE: [
            TreatmentsEnum.SPLINT,
            TreatmentsEnum.PAIN_MEDICATIONS,
            TreatmentsEnum.FENTANYL_LOLLIPOP,
        ],
        # IV fluids and blood transfusion as needed, plus pain relief for internal injuries.
        InjuryTypeEnum.INTERNAL: [
            TreatmentsEnum.IV_BAG,
            TreatmentsEnum.BLOOD,
            TreatmentsEnum.PAIN_MEDICATIONS,
        ],
        # Pain management, oxygen monitoring, and IV fluids for brain injury support.
        InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY: [
            TreatmentsEnum.PAIN_MEDICATIONS,
            TreatmentsEnum.PULSE_OXIMETER,
            TreatmentsEnum.IV_BAG,
        ],
        # Bandage and gauze to control bleeding, pain relief, and IV fluids for stabilization.
        InjuryTypeEnum.OPEN_ABDOMINAL_WOUND: [
            TreatmentsEnum.PRESSURE_BANDAGE,
            TreatmentsEnum.HEMOSTATIC_GAUZE,
            TreatmentsEnum.PAIN_MEDICATIONS,
            TreatmentsEnum.IV_BAG,
        ],
    }

    CONTRAINDICATED_TREATMENTS = {
        # Applying a tourniquet, decompression needle, or airway for ear bleeding is inappropriate.
        InjuryTypeEnum.EAR_BLEED: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.NASOPHARYNGEAL_AIRWAY,
        ],
        # For asthma attacks, avoid tourniquet, bandage, and decompression, as they are ineffective or harmful.
        InjuryTypeEnum.ASTHMATIC: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.PRESSURE_BANDAGE,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
        ],
        # Decompression needles and tourniquets are unnecessary and harmful for surface cuts.
        InjuryTypeEnum.LACERATION: [
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.TOURNIQUET,
        ],
        # Avoid tourniquet and decompression for puncture wounds, as these treatments don’t address the injury type.
        InjuryTypeEnum.PUNCTURE: [
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.TOURNIQUET,
        ],
        # Tourniquet and decompression needle are inappropriate for managing shrapnel injuries.
        InjuryTypeEnum.SHRAPNEL: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
        ],
        # Avoid tourniquet, bandage, and airway for collapsed lung as they do not aid respiratory issues effectively.
        InjuryTypeEnum.CHEST_COLLAPSE: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.PRESSURE_BANDAGE,
            TreatmentsEnum.NASOPHARYNGEAL_AIRWAY,
        ],
        # Decompression needle and bandage are unsuitable for amputations; bleeding needs advanced interventions.
        InjuryTypeEnum.AMPUTATION: [
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.PRESSURE_BANDAGE,
        ],
        # Tourniquet, hemostatic gauze, decompression, and airway management are unsuitable for burns.
        InjuryTypeEnum.BURN: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.HEMOSTATIC_GAUZE,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.NASOPHARYNGEAL_AIRWAY,
        ],
        # Avoid tourniquet and decompression needle for minor scrapes.
        InjuryTypeEnum.ABRASION: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
        ],
        # Tourniquet, decompression needle, and airway are not suitable for treating fractures.
        InjuryTypeEnum.BROKEN_BONE: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.NASOPHARYNGEAL_AIRWAY,
        ],
        # Avoid tourniquet, decompression needle, and airway for internal injuries as they don't address internal trauma.
        InjuryTypeEnum.INTERNAL: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
        ],
        # Tourniquet, decompression, gauze, and airway management are ineffective and inappropriate for brain injuries.
        InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.HEMOSTATIC_GAUZE,
            TreatmentsEnum.NASOPHARYNGEAL_AIRWAY,
        ],
        # Tourniquet, decompression needle, splint, and airway are unsuitable for abdominal wounds.
        InjuryTypeEnum.OPEN_ABDOMINAL_WOUND: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.SPLINT,
            TreatmentsEnum.NASOPHARYNGEAL_AIRWAY,
        ],
    }

    LOCATION_CONTRAINDICATED_TREATMENTS = {
        # Head and neck areas: Tourniquets and decompression needles can cause harm without benefit.
        InjuryLocationEnum.HEAD: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
        ],
        InjuryLocationEnum.NECK: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
        ],
        InjuryLocationEnum.LEFT_NECK: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
        ],
        InjuryLocationEnum.RIGHT_NECK: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
        ],
        # Chest and side areas: Tourniquets and splints do not stabilize or aid injuries in these regions.
        InjuryLocationEnum.RIGHT_CHEST: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.SPLINT,
        ],
        InjuryLocationEnum.LEFT_CHEST: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.SPLINT,
        ],
        InjuryLocationEnum.CENTER_CHEST: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.SPLINT,
        ],
        InjuryLocationEnum.RIGHT_SIDE: [TreatmentsEnum.TOURNIQUET],
        InjuryLocationEnum.LEFT_SIDE: [TreatmentsEnum.TOURNIQUET],
        # Stomach areas: Tourniquets, decompression needles, and splints are ineffective here.
        InjuryLocationEnum.RIGHT_STOMACH: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.SPLINT,
        ],
        InjuryLocationEnum.LEFT_STOMACH: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.SPLINT,
        ],
        InjuryLocationEnum.STOMACH: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
            TreatmentsEnum.SPLINT,
        ],
        # Face areas: Tourniquets cannot be applied effectively to facial injuries.
        InjuryLocationEnum.LEFT_FACE: [TreatmentsEnum.TOURNIQUET],
        InjuryLocationEnum.RIGHT_FACE: [TreatmentsEnum.TOURNIQUET],
        # Internal injuries: Tourniquets and decompression needles are ineffective for internal trauma.
        InjuryLocationEnum.INTERNAL: [
            TreatmentsEnum.TOURNIQUET,
            TreatmentsEnum.DECOMPRESSION_NEEDLE,
        ],
    }

    BLOOD_TREATMENT_RULES = {
        # Blood transfusion is typically appropriate for these severe injuries
        # where significant blood loss is likely and fluid resuscitation is needed.
        "valid_injury_types": [
            # Major blood loss due to limb loss requires blood replacement.
            InjuryTypeEnum.AMPUTATION,
            # Internal bleeding often necessitates blood transfusion for stabilization.
            InjuryTypeEnum.INTERNAL,
            # Severe blood loss risk with open abdominal wounds.
            InjuryTypeEnum.OPEN_ABDOMINAL_WOUND,
        ],
        # Blood transfusion is generally contraindicated in head and neck injuries
        # to avoid increased intracranial pressure or other complications.
        "contraindicated_injury_locations": [
            # Blood transfusion in head injuries can worsen intracranial pressure.
            InjuryLocationEnum.HEAD,
            # Neck injuries risk airway compromise; blood is not typically prioritized.
            InjuryLocationEnum.NECK,
            # Same rationale as neck; high risk of airway and vascular complications.
            InjuryLocationEnum.LEFT_NECK,
            # Same as above; avoid blood transfusion due to airway and vascular concerns.
            InjuryLocationEnum.RIGHT_NECK,
        ],
    }

    SUPPLY_AND_VITAL_RULES = {
        (SupplyTypeEnum.DECOMPRESSION_NEEDLE, "breathing", BreathingLevelEnum.NONE): [
            TreatmentsEnum.DECOMPRESSION_NEEDLE
        ],
        (SupplyTypeEnum.VENTED_CHEST_SEAL, "spo2", BloodOxygenEnum.LOW): [
            TreatmentsEnum.VENTED_CHEST_SEAL
        ],
        (
            SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY,
            "mental_status",
            MentalStatusEnum.UNRESPONSIVE,
        ): [TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
        (SupplyTypeEnum.BLOOD, "spo2", BloodOxygenEnum.LOW): [TreatmentsEnum.BLOOD],
        (SupplyTypeEnum.IV_BAG, "hrpmin", HeartRateEnum.FAINT): [TreatmentsEnum.IV_BAG],
    }

    def get_valid_treatments(
        self, injury: Injury, vitals: Vitals, supplies: List[SupplyTypeEnum]
    ) -> List[TreatmentsEnum]:
        """
        Determines valid treatments based on injury, casualty vitals, and available supplies.
        """
        valid_treatments = set()

        # Add treatments specific to the injury type
        injury_valid_treatments = self.VALID_TREATMENTS.get(injury.name, [])
        valid_treatments.update(injury_valid_treatments)

        # Add treatments based on both supplies and vitals
        for supply in supplies:
            for (
                supply_type,
                vital_attr,
                vital_value,
            ), treatments in self.SUPPLY_AND_VITAL_RULES.items():
                if (
                    supply.type == supply_type
                    and getattr(vitals, vital_attr, None) == vital_value
                ):
                    valid_treatments.update(treatments)

        return list(valid_treatments)

    def get_contraindicated_treatments(self, injury: Injury) -> List[TreatmentsEnum]:
        """
        Returns a list of treatments that are contraindicated for the specified injury type.
        """
        return self.CONTRAINDICATED_TREATMENTS.get(injury.name, [])

    def get_location_contraindicated_treatments(
        self, injury: Injury
    ) -> List[TreatmentsEnum]:
        """
        Returns a list of contraindicated treatments based on injury location.
        """
        location_enum = InjuryLocationEnum(injury.location)
        return self.LOCATION_CONTRAINDICATED_TREATMENTS.get(location_enum, [])

    def is_blood_treatment_valid(self, injury: Injury) -> bool:
        """
        Determines if 'Blood' treatment is valid for the specified injury.
        """
        # Check if the injury type is valid for blood treatment
        if injury.name not in self.BLOOD_TREATMENT_RULES["valid_injury_types"]:
            return False

        # Check if the injury location is contraindicated for blood treatment
        if (
            InjuryLocationEnum(injury.location)
            in self.BLOOD_TREATMENT_RULES["contraindicated_injury_locations"]
        ):
            return False

        return True