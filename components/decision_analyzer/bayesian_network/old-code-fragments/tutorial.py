import torch, numpy

from pomegranate.distributions import Categorical
from pomegranate.distributions import ConditionalCategorical
from pomegranate.bayesian_network import BayesianNetwork

d1 = Categorical([[0.1, 0.9]])
d2 = ConditionalCategorical([[[0.4, 0.6], [0.3, 0.7]]])

model = BayesianNetwork([d1, d2], [(d1, d2)])

X = numpy.random.randint(2, size=(10, 2))
model.fit(X)

model.distributions[0].probs, X[:,0].mean()

model.distributions[1].probs[0], (X[X[:,0] == 0][:,1]).mean()

model.probability(X)
model.distributions[0].log_probability(X[:,:1]) + model.distributions[1].log_probability(X[:, :, None])
print(X)
X_torch = torch.tensor(X[:4])
print(X_torch)
mask = torch.tensor([[True, False],
                     [False, True],
                     [True, True],
                     [False, False]])

# Okay, it looks like every *row* of the tensor is a separate observation.
# And column idx is the value (converted to int) that random variable idx takes for that observation.
# And finally, the mask says whether the corresponding value is actually observed.

X_masked = torch.masked.MaskedTensor(torch.tensor(X[:1]), mask=torch.tensor([[False, False]]))
print(f"{X_masked=}")
a = model.predict_proba(X_masked)
print(f"{a=}")
X_masked = torch.masked.MaskedTensor(X_torch, mask=mask)
print(f"{X_masked=}")
a = model.predict_proba(X_masked)
print(a)
