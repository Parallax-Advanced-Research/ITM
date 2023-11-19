from app import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
import enum
import pandas as pd
import random


class ExtendedEnum(enum.Enum):
    @classmethod
    def get_members(cls):
        return [member.value for name, member in cls.__members__.items()]

    @classmethod
    def get_member(cls, value):
        return cls.__members__.get(value, None)

    @classmethod
    def get_member_name(cls, value):
        member = cls.get_member(value)
        return member.name if member else None

    @classmethod
    def get_member_value(cls, name):
        member = cls.__members__.get(name, None)
        return member.value if member else None


class MissionTypes(ExtendedEnum):
    LISTENING_OBSERVATION = "Listening/Observation"
    DIRECT_ACTION = "Direct Action"
    HOSTAGE_RESCUE = "Hostage rescue"
    ASSET_TRANSPORT = "Asset transport"
    SENSOR_EMPLACEMENT = "Sensor emplacement"
    INTELLIGENCE_GATHERING = "Intelligence gathering"
    CIVIL_AFFAIRS = "Civil affairs"
    TRAINING = "Training"
    SABOTAGE = "Sabotage"
    SECURITY_PATROL = "Security patrol"
    FIRE_SUPPORT = "Fire support"
    NUCLEAR_DETERRENCE = "Nuclear deterrence"
    EXTRACTION = "Extraction"
    UNKNOWN = "Unknown"


class SupplyTypes(ExtendedEnum):
    TOURNIQUET = "Tourniquet"
    PRESSURE_BANDAGE = "Pressure bandage"
    HEMOSTATIC_GAUZE = "Hemostatic gauze"
    DECOMPRESSION_NEEDLE = "Decompression Needle"  # in ta1 data Decompression Needle
    NASPHARYNGEAL_AIRWAY = "Nasopharyngeal airway"


class RelationshipTypes(ExtendedEnum):
    NONE = "None"
    ALLY = "Ally"
    FRIEND = "Friend"
    HOSTILE = "Hostile"
    EXPECTANT = "Expectant"


class RankTypes(ExtendedEnum):
    MARINE = "Marine"
    FMF_CORPSMAN = "FMF Corpsman"
    SAILOR = "Sailor"
    CIVILIAN = "Civilian"
    SEAL = "SEAL"
    INTEL_OFFICER = "Intel Officer"


class AttributeTag(db.Model):
    __tablename__ = "attributetag"
    id = db.Column(db.Integer, primary_key=True)
    attribute_category = db.Column(db.String(64), index=True)
    attribute_name = db.Column(db.String(64), index=True)
    attribute_description = db.Column(db.String(256))
    attribute_value = db.Column(db.String(64), index=True)
    attribute_type = db.Column(db.String(64), index=True)
    attribute_max = db.Column(db.Integer)
    attribute_min = db.Column(db.Integer)
    attribute_unit = db.Column(db.String(64), index=True)
    attribute_default = db.Column(db.String(64), index=True)
    attribute_options = db.Column(db.String(256))


# Attribute Tag Self Relation table
class AttributeTagRelation(db.Model):
    __tablename__ = "attributetagrelation"
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("attributetag.id"))
    child_id = db.Column(db.Integer, db.ForeignKey("attributetag.id"))
    parent = db.relationship(
        "AttributeTag",
        backref="children",
        primaryjoin=(parent_id == AttributeTag.id),
        lazy="joined",
    )
    child = db.relationship(
        "AttributeTag",
        backref="parents",
        primaryjoin=(child_id == AttributeTag.id),
        lazy="joined",
    )


class CaseBase(db.Model):
    __tablename__ = "casebase"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    description = db.Column(db.String(256))
    created_by = db.Column(db.String(64), default="admin")
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    cases = db.relationship("Case", backref="casebase", lazy="dynamic")

    def __repr__(self):
        return "<CaseBase {}>".format(self.name)

    def train(self):
        pass

    def evaluate():
        pass

    def as_dataframe(self, feature_as_action, do_analysis=False):
        casebase_df = pd.DataFrame()
        for case in self.cases:
            caselist = case.as_ta3dict_list(feature_as_action, do_analysis)
            case_df = pd.DataFrame(caselist)
            casebase_df = pd.concat([casebase_df, case_df])
        return casebase_df

    def as_ta1dataframe(self, feature_as_action):
        casebase_df = pd.DataFrame()
        for case in self.cases:
            caselist = case.as_ta1dict_list(feature_as_action)
            case_df = pd.DataFrame(caselist)
            casebase_df = pd.concat([casebase_df, case_df])
        return casebase_df

    def save(self):
        db.session.add(self)
        db.session.commit()


class Case(db.Model):
    __tablename__ = "case"
    id = db.Column(Integer, primary_key=True)
    external_id = db.Column(String(50), nullable=True)
    name = db.Column(String(50), nullable=False, default="case " + id)
    time_stamp = db.Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(String(50), nullable=True)
    casebase_id = db.Column(Integer, db.ForeignKey("casebase.id"), nullable=False)
    scenarios = db.relationship(
        "Scenario",
        secondary="case_scenario",
        backref="cases",
        lazy="dynamic",
        cascade="all, delete",
    )

    def analyze(self):
        pass

    def select_decision(self):
        pass

    def evaluate():
        pass

    def as_dict_list(self):
        case_dict_list = []
        case_dict = {}
        for scenario in self.scenarios:
            supplies_dict = {}
            casualty_dict = {}

            for i in range(len(scenario.supplies)):
                val = scenario.supplies[i].get_feature_dict()
                supply_type = val["supply_type"]
                supply_count = val["supply_quantity"]

                supply = "supply" + str(i + 1)
                supply_quantity = "supply_quantity" + str(i + 1)

                supplies_dict.update({supply: supply_type})
                supplies_dict.update({supply_quantity: supply_count})
            print(supplies_dict)
            """
            for i in range(len(scenario.supplies)):
                val = scenario.supplies[i].get_single_feature_dict()
                supplies_dict.update(val)
            """
            for i in range(len(scenario.casualties.all())):
                val = scenario.casualties[i].get_feature_dict()
                cas = "casualty" + str(i + 1)
                cas_id = "casualty_id" + str(i + 1)
                cas_name = "casualty_name" + str(i + 1)
                cas_age = "casualty_age" + str(i + 1)

                cas_id_val = val["id"]
                cas_name_val = val["name"]
                cas_age_val = val["age"]

                casualty_dict.update({cas_name: cas_name_val})
                casualty_dict.update({cas_age: cas_age_val})

            print(casualty_dict)

            for probe in scenario.probes:
                case_dict.update(probe.get_feature_dict())

                for response in probe.responses:
                    case_dict.update(response.get_feature_dict())
                    for kdma in response.kdmas:
                        case_dict.update(kdma.get_feature_dict())

                    # case_dict.update(supplies_dict)
                    # case_dict.update(casualty_dict)
                    case_dict_list.append(case_dict.copy())

                    # print(case_dict)
        return case_dict_list

    def as_ta3dict_list(self, feature_as_action, do_analysis):
        case_dict_list = []
        case_dict = {}
        for scenario in self.scenarios:
            for probe in scenario.probes:
                if do_analysis:
                    try:
                        metrics, bn_metrics = probe.analyze()
                    except:
                        metrics = {}
                        bn_metrics = {}

                case_dict.update(probe.get_feature_dict())
                for response in probe.responses:
                    # case_dict.update(response.get_feature_dict())
                    for i in range(len(response.actions)):
                        casualty_name = response.actions[i].casualty.name
                        val = response.actions[i].get_feature_dict()
                        action_type = val["action_type"]
                        action = "action" + str(i + 1)
                        action_type = "action_type" + str(i + 1)
                        action_type_val = val["action_type"]
                        case_dict.update({action: action_type_val})

                        if response.actions:
                            tag_dict = {
                                "tag": "None",
                            }
                            treat_dict = {
                                "treatment": "None",
                            }
                            location_dict = {
                                "location": "None",
                            }

                            analysis_dict = {}

                            # the montecarlo values
                            if do_analysis:
                                # severity to dict
                                analysis_dict = {
                                    "SEVERITY": "None",
                                    "SUPPLIES_REMAINING": "None",
                                    "AVERAGE_TIME_USED": "None",
                                    "DAMAGE_PER_SECOND": "None",
                                    "MEDSIM_P_DEATH": "None",
                                    "SEVERITY_CHANGE": "None",
                                    "SUPPLIES_USED": "None",
                                    "ACTION_TARGET_SEVERITY": "None",
                                    "ACTION_TARGET_SEVERITY_CHANGE": "None",
                                    "SEVEREST_SEVERITY": "None",
                                    "SEVEREST_SEVERITY_CHANGE": "None",
                                    "NONDETERMINISM": "None",
                                }

                                if action_type_val == "CHECK_ALL_VITALS":
                                    for metric in enumerate(metrics):
                                        label = metric[1]
                                        if label.find(casualty_name) != -1:
                                            for key, value in metrics[label].items():
                                                analysis_dict.update({key: value.value})

                                current_bn_action = bn_metrics[action]
                                bn_dict = {
                                    "pDeath": "None",
                                    "pPain": "None",
                                    "pBrainInjury": "None",
                                    "pAirwayBlocked": "None",
                                    "pInternalBleeding": "None",
                                    "pExternalBleeding": "None",
                                }
                                for key, value in current_bn_action.items():
                                    bn_dict.update({key: value.value})
                                case_dict.update(bn_dict)

                            for parameter in response.actions[i].parameters:
                                if parameter.parameter_type == "tag":
                                    # the first dictionary in metrics
                                    if do_analysis:
                                        for metric in enumerate(metrics):
                                            # the label of the first dictionary
                                            label = metric[1]
                                            # if the label contains the matching action type, it corresponds to the current tag action
                                            # so this is the matching metrics dictionary
                                            if (
                                                label.find(parameter.parameter_value)
                                                != -1
                                            ):
                                                # extract inner dictionary
                                                for key, value in metrics[
                                                    label
                                                ].items():
                                                    # add the inner dictionary to the tag dictionary
                                                    analysis_dict.update(
                                                        {key: value.value}
                                                    )
                                    tag_dict.update(parameter.get_feature_dict())
                                if parameter.parameter_type == "treatment":
                                    if do_analysis:
                                        # the second dictionary in metrics
                                        for metric in enumerate(metrics):
                                            # the label of the second dictionary
                                            label = metric[1]
                                            # if the label contains the matching action type, it corresponds to the current treatment action
                                            # so this is the matching metrics dictionary
                                            if (
                                                label.find(parameter.parameter_value)
                                                != -1
                                            ):
                                                # extract inner dictionary
                                                for key, value in metrics[
                                                    label
                                                ].items():
                                                    # add the inner dictionary to the treatment dictionary
                                                    analysis_dict.update(
                                                        {key: value.value}
                                                    )
                                    treat_dict.update(parameter.get_feature_dict())
                                if parameter.parameter_type == "location":
                                    location_dict.update(parameter.get_feature_dict())
                            case_dict.update(analysis_dict)

                            if feature_as_action:
                                case_dict.update(tag_dict)
                                case_dict.update(treat_dict)
                                case_dict.update(location_dict)
                            else:
                                case_dict.update(
                                    {
                                        action: action_type_val
                                        + " "
                                        + tag_dict["tag"]
                                        + " "
                                        + treat_dict["treatment"]
                                        + " "
                                        + location_dict["location"]
                                    }
                                )

                            # case_dict.update(tag_dict)
                            # case_dict.update(treat_dict)
                            # case_dict.update(location_dict)

                        case_dict.update({"casualty_name": casualty_name})
                        case_dict.update(
                            {"casualty_age": response.actions[i].casualty.age}
                        )
                        case_dict.update(
                            {"casualty_sex": response.actions[i].casualty.sex}
                        )
                        case_dict.update(
                            {"casualty_rank": response.actions[i].casualty.rank}
                        )
                        injuries = response.actions[i].casualty.injuries
                        injury = injuries[-1]

                        case_dict.update({"injury_type": injury.injury_type})
                        case_dict.update({"injury_severity": injury.injury_severity})
                        case_dict.update({"injury_location": injury.injury_location})

                    for kdma in response.kdmas:
                        case_dict.update(kdma.get_feature_dict())

                    case_dict_list.append(case_dict.copy())

        return case_dict_list

    def as_ta1dict_list(self, feature_as_action):
        case_dict_list = []
        case_dict = {}
        for scenario in self.scenarios:
            for probe in scenario.probes:
                probe_type = probe.type
                probe_prompt = "What do you do?"
                probe_info_dict = {
                    "type": probe_type,
                    "prompt": probe_prompt,
                }
                for response in probe.responses:
                    for action in response.actions:
                        case_dict.update(probe_info_dict)
                        action_type = action.action_type
                        action_info_dict = {
                            "action1": action_type,
                        }
                        tag_dict = {
                            "tag": "None",
                        }
                        treat_dict = {
                            "treatment": "None",
                        }
                        location_dict = {
                            "location": "None",
                        }

                        for parameter in action.parameters:
                            if parameter.parameter_type == "tag":
                                tag_dict.update(parameter.get_feature_dict())
                            if parameter.parameter_type == "treatment":
                                treat_dict.update(parameter.get_feature_dict())
                            if parameter.parameter_type == "location":
                                location_dict.update(parameter.get_feature_dict())

                            new_action_1 = {
                                "action1": action_info_dict["action1"]
                                + " "
                                + tag_dict["tag"]
                                + " "
                                + treat_dict["treatment"].upper()
                                + " "
                                + location_dict["location"]
                            }

                            if feature_as_action:
                                case_dict.update(action_info_dict)
                                case_dict.update(treat_dict)
                                case_dict.update(location_dict)
                            else:
                                case_dict.update(new_action_1)
                        case_dict.update({"casualty_name": action.casualty.name})
                        case_dict.update({"casualty_age": action.casualty.age})
                        case_dict.update({"casualty_sex": action.casualty.sex})
                        case_dict.update({"casualty_rank": action.casualty.rank})
                        injuries = action.casualty.injuries
                        injury = injuries[-1]

                        case_dict.update({"injury_type": injury.injury_type})
                        case_dict.update({"injury_severity": injury.injury_severity})
                        case_dict.update({"injury_location": injury.injury_location})

                        kdma_dict = {
                            "mission": 0,
                            "denial": 0,
                            "risktol": 0,
                            "timeurg": 0,
                        }

                        for kdma in response.kdmas:
                            if kdma.kdma_name == "Utilitarianism":
                                kdma_dict.update({"mission": kdma.kdma_value})
                            if kdma.kdma_name == "Fairness":
                                kdma_dict.update({"denial": kdma.kdma_value})
                            if kdma.kdma_name == "RiskAversion":
                                kdma_dict.update({"risktol": kdma.kdma_value})
                            if kdma.kdma_name == "TimePressure":
                                kdma_dict.update({"timeurg": kdma.kdma_value})

                        case_dict.update(kdma_dict)
                        case_dict_list.append(case_dict.copy())

        return case_dict_list

    def save(self):
        db.session.add(self)
        db.session.commit()


case_scenario = db.Table(
    "case_scenario",
    db.Model.metadata,
    db.Column("case_id", db.Integer, db.ForeignKey("case.id")),
    db.Column("scenario_id", db.Integer, db.ForeignKey("scenario.id")),
)
