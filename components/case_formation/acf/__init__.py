import sys
sys.path.append('.')

from domain.internal import Probe
sys.path.append('.')
import yaml
from domain.internal import Probe, State, Decision, KDMAs, Scenario, DecisionMetric
from components import DecisionAnalyzer
from components.decision_analyzer import *
# there will probably be a default here. Also, we will probably just call Decision Analyzer
from components.decision_analyzer.event_based_diagnosis.ebd_analyzer import EventBasedDiagnosisAnalyzer

# just to run it from this location for now