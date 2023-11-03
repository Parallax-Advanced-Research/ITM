DEBUG = True


in_notebook = False
try:
	from IPython import get_ipython
	if get_ipython() is not None and 'IPKernelApp' in get_ipython().config:
		from IPython.display import display, Math, Latex,HTML
		import pyAgrum.lib.notebook as gnb
		import pyAgrum.causal.notebook as cslnb
		in_notebook = True
except:
	pass

import pyAgrum as gum
import pyAgrum.causal as csl


#net = gum.fastBN("Smoking->Cancer")
net = gum.fastBN("Clouds{F|T}->Rain{F|T};Rain->Sprinkler{F|T}->Wet{F|T};Zeus{F|T}->Rain;Rain->Wet")

net.cpt("Zeus")[:]=[0.85,0.15]

net.cpt("Clouds")[:]=[0.75,0.25]

net.cpt("Rain")[{"Clouds":'F', "Zeus": 'F'}]=[0.97, 0.03]
net.cpt("Rain")[{"Clouds":'F', "Zeus": 'T'}]=[0.4, 0.6]
net.cpt("Rain")[{"Clouds":'T', "Zeus": 'F'}]=[0.32, 0.68]
net.cpt("Rain")[{"Clouds":'T', "Zeus": 'T'}]=[0.1, 0.9]

net.cpt("Sprinkler")[{"Rain": 'F'}] = [0.55, 0.45]
net.cpt("Sprinkler")[{"Rain": 'T'}] = [0.88, 0.12]
	
net.cpt("Wet")[{ "Rain": 'F', "Sprinkler": 'F'}] = [ 1.0,  0.0  ]
net.cpt("Wet")[{ "Rain": 'F', "Sprinkler": 'T'}] = [ 0.21, 0.79 ]
net.cpt("Wet")[{ "Rain": 'T', "Sprinkler": 'F'}] = [ 0.18, 0.82 ]
net.cpt("Wet")[{ "Rain": 'T', "Sprinkler": 'T'}] = [ 0.02, 0.98 ]

evidence = {"Zeus" : "T"}

if DEBUG and in_notebook:
	gnb.flow.row(
	               net,
	               net.cpt("Clouds")*net.cpt("Rain")*net.cpt("Sprinkler")*net.cpt("Wet"),
	               net.cpt("Clouds"),
	               net.cpt("Zeus"),
	               net.cpt("Rain"),
	               net.cpt("Sprinkler"),
	               net.cpt("Wet"),
	captions=["the BN","the joint distribution","$Clouds$","Zeus", "$Rain$", "Sprinkler", "Wet"])

	print("=====================")

	gnb.showInference(net, evs=evidence)

ie = gum.LazyPropagation(net)
ie.setEvidence(evidence)
ie.makeInference()
ie.posterior("Wet")


print("P(Wet | evidence) = ", ie.posterior('Wet')[:])

print('foo')
