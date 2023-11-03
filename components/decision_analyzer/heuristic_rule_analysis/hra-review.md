# `make_dspace permutation`
* should raise an exception on error instead of returning string. Or
  alternately, the caller should check the return type to determine if it was
  an error value, but an exception is probably the simpler option here.

# `take_the_best`:
* for annotating tuples, specify the types of what's in the tuple as such:
  `Tuple[int,str]` (will need `from typing import Tuple` to get the Tuple symbol)

* Maybe define a namedtuple or simple class for the return type of
  `take_the_best`. More self-documenting than returning either a 2-tuple or a
  3-tuple.

* Maybe call `treatment_idx` `treatment_keys`. idx makes me think it's a single
  index (and an integral one at that, but that might just be me.)

* Close the file as soon as you've loaded it into the json object.


# `one_bounce`
* comment for `battle` is inconsistent with how it's used.

* initialize `battle` as
  ```battle: List[List[Tuple[int,int]]] = [[]]*len(treatment_idx)```
  Then you can drop the `if battle[first] == None` branch.
  Might also make `battle[-1] = list()` unnecessary, assuming first is never
  equal to `len(treatment_idx) - 1`.

* `raise Exception("no battles")` instead of `return "no battles"`

* defines `treatment_sums` but never uses it.

* If `len(battle) >= 1 and len(battle[0]) < 1`, it's possible to get to the
  `battle[winner_idx][battle_idx]` expression while both of those indices are
  None. Not entirely sure what the "loop through battle pairs" section of code is
  meant to do, but it seems like a roundabout way of doing it.


# `choose_next_casualty`
* dict type specifiers are defined like this: `Dict[str, int]`. First arg is the
  key type; second is the value.

* `next_casualty_id` sounds singular, but it's a list.

* Doesn't use `kdma_list` or `injury_list`

* `if injury == "Burn" or injury == "Forehead Scrape" or injury == "Laceration":`
  -> `injury in ("Burn", "Forehead Scrape", "Laceration")`.
  Similarly elsewhere.


# `analyze`
* formatting: put each key:val on its own line for `casualty_data[ele.id] = ...`

* redundant code? It looks like the same stuff is being written to `new_file` twice.

* is there a reason `casualty_data` is being converted to a dictionary and
  written to a file and then the filename is passed to `hra_decision_analytics`
  instead of passing the Casualty object directly? (Even if there's a need to
  have the file, better to read the file back into a Casualty object instead of a
  json, so we get the static type checking)

* Type of `scen` needs to be `Scenario[TA3State]`. Same for `probe: Probe[TA3State]`

* `analysis` variable unused.


# `convert_between_kdma_risk_reward_ratio`
* predictor not used
* return string -> raise Exception

* What does this return? One branch returns a dictionary, one returns a string,
  and one returns nothing.
  Same questions for the other `convert_between_kdma_foo` functions.


# `hra_decision_analytics`

In this code:
```
risk_reward_ratio = 'risk_reward_ratio'
resources = 'resources'
time = 'time'
system = 'system'

predictors = {risk_reward_ratio:self.convert_between_kdma_risk_reward_ratio(mission, denial, None),\
			  resources:self.convert_between_kdma_resources(mission, denial, None),\
			  time:self.convert_between_kdma_time(mission, denial, None),\
			  system:self.convert_between_kdma_system(mission, denial, None)}
```
.. there's no benefit to having key names as separate variables if they're only used here. It might make sense if they were defined in a config file or something (probably also unnecessary).


# `update_metrics`
* `Decision` needs to be `Decision[TA3State]`


# Misc
* Some functions missing comment describing what their args and outputs are.

* pathlib.Path imported but unused

* The `"""foo"""` comments for functions go after the prototype line. (That's where
  python looks when deciding what to print for `help(fnc)`, so we're stuck with
  it.)

* Why are the comments all indented to the same level but with dashes to indicate
  level of indentation? Does some editor use the dashes to decide how to display
  the comments?

* Add type annotations to all functions.



## duplicate code
Lot of duplicate code at the front of `take_the_best`, `exhaustive`, etc. Although a lot of it is either setting locals or returning...maybe pull the non-duplicate parts out into a separate function that does the middle bits. Something like this:

```
class SelectedTreatment:
	def __init__(self, treatment_name: str, treatment_info: Dict[str, Union[str, List[str]]], search_tree: str) -> None:
		self.treatment_name = treatment_name
		self.treatment_info = treatment_info
		self.search_tree = search_tree

Treatment_Info = Dict[str, Dict[str, Any]]
Heuristic_Fnc = Callable[[List[int], str], Heuristic_Rule_Analyzer, List[str], Treatment_Info] # I'm not sure this is the right signature. Probably needs to be a bit more general since some of the functions take more args, e.g., `seed`, `m`.

def make_decision(self, strategy: Heuristic_Fnc, file_name: str, search_path: bool = False) -> SelectedTreatment:
	
	# prep inputs
	f = open(file_name)

	# get dict from data and convert treatment dict to list
	data: Dict[str, Dict[str, Any]] = json.load(f)
	f.close()
	treatment_idx = list(data['treatment'])

	# if there is only a single treatment in the decision space
	if len(treatment_idx) == 1:
		return (treatment_idx[0], data['treatment'][treatment_idx[0]])


	# Search-strategy-specific stuff
	list_indices, search_tree = fnc(self, treatment_idx, data)


	#  if there is not tie, the treatment with the max value wins
	if len(list_indices) == 1:

		#  return treatment, info pair corresponding to max index or "no preference"
		if search_path:
			return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]], search_tree)
		else:
			return (treatment_idx[list_indices[0]], data['treatment'][treatment_idx[list_indices[0]]])
	else:
		if search_path:
			return ("no preference", "", search_tree)
		else:
			return ("no preference", "")

```

## open
* For `open()` calls, pass an `encoding='utf-8'` argument.

* When opening a file, a good approach is:
```
with open(fname, encoding='utf-8') as f:
	do stuff with f
```

instead of

```
f = open(fname, encoding='utf-8')
do stuff with f
f.close()
```
since it guarantees that f gets closed even if something in do stuff raises an exception.

