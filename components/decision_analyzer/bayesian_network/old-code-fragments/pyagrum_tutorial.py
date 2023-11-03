from IPython.display import display, Math, Latex,HTML

import pyAgrum as gum
import pyAgrum.lib.notebook as gnb
import pyAgrum.causal as csl
import pyAgrum.causal.notebook as cslnb



obs1 = gum.fastBN("Smoking->Cancer")

obs1.cpt("Smoking")[:]=[0.6,0.4]
obs1.cpt("Cancer")[{"Smoking":0}]=[0.9,0.1]
obs1.cpt("Cancer")[{"Smoking":1}]=[0.7,0.3]

gnb.flow.row(obs1,obs1.cpt("Smoking")*obs1.cpt("Cancer"),obs1.cpt("Smoking"),obs1.cpt("Cancer"),
               captions=["the BN","the joint distribution","the marginal for $smoking$","the CPT for $cancer$"])
print('foo')
