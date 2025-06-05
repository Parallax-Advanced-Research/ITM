# Analysis of Command-Line Arguments Used in ins_online_learning.py

## Arguments from get_default_parser() that are ACTUALLY USED:

### Used directly in ins_online_learning.py:
1. **`--seed`** - Used to set and get the global random seed (lines 36-39)
2. **`--restart_pid`** - Used to restart from a previous run (lines 41-44)
3. **`--exp_name`** - Used for directory/file naming (lines 42, 76, 139)
4. **`--session_type`** - Used to find scenario files and construct scenario IDs (lines 47, 61, 65, 102, 106)
5. **`--endpoint`** - Checked for None value (line 56)
6. **`--exp_file`** - Used to read train/test scenario configurations (lines 93-98)
7. **`--scenario`** - Set dynamically for each scenario being run (lines 127, 143)

### Set but not used in ins_online_learning.py (passed to other components):
1. **`args.training`** - Set to True (line 30)
2. **`args.keds`** - Set to False (line 31)
3. **`args.verbose`** - Set to False (line 32)
4. **`args.dump`** - Set to False (line 33)
5. **`args.uniformweight`** - Set to True (line 34)
6. **`args.case_file`** - Set conditionally based on restart_pid (line 44)
7. **`args.selector_object`** - Set to the seeker object (line 90)
8. **`args.ta3_port`** - Set from environment variable (line 115)
9. **`args.pid`** - Set to current process ID (line 116)

### Arguments specific to ins_online_learning.py (added via parser.add_argument):
1. **`--critic`** - Used by InsuranceOnlineApprovalSeeker (line 18)
2. **`--train_weights`** - Used by InsuranceOnlineApprovalSeeker (line 19)
3. **`--selection_style`** - Used by InsuranceOnlineApprovalSeeker (line 20)
4. **`--search_style`** - Used by InsuranceOnlineApprovalSeeker (line 21)
5. **`--learning_style`** - Used by InsuranceOnlineApprovalSeeker (line 22)
6. **`--restart_entries`** - Checked but code is commented out (lines 23, 86-87, 112-113)
7. **`--reveal_kdma`** - Used by InsuranceOnlineApprovalSeeker (line 25)
8. **`--estimate_with_discount`** - Used by InsuranceOnlineApprovalSeeker (line 26)

## Arguments from get_default_parser() that are NOT USED:
- `--verbose` (overridden to False)
- `--dump` (overridden to False)
- `--rollouts`
- `--variant`
- `--kdma/--kdmas`
- `--training` (overridden to True)
- `--connect_to_ta1`
- `--alignment_target`
- `--evaltarget/--eval_targets`
- `--selector`
- `--assessor`
- `--case_file` (only set conditionally, not read from parser)
- `--weight_file`
- `--uniform_weight` (overridden as uniformweight)
- `--decision_verbose`
- `--insert_pauses`
- `--ignore_relevance`
- `--elab_output`
- `--record_considered_decisions`
- `--bypass_server_check`
- `--domain_package`
- `--domain_class_name`
- All the analyzer flags (`--ebd`, `--mc`, `--br`, `--bayes`)
- All the deprecated selector flags (`--keds`, `--kedsd`, `--csv`, `--human`)

## Arguments used by InsuranceOnlineApprovalSeeker:
From the init_with_args method (lines 75-88):
1. `args.kdmas` - Used to extract the arg_name (line 78)
2. `args.critic` - Used to filter critics (lines 80-81)
3. `args.train_weights` - Stored (line 82)
4. `args.selection_style` - Stored (line 83)
5. `args.learning_style` - Stored (line 84)
6. `args.search_style` - Stored (line 85)
7. `args.reveal_kdma` - Stored (line 86)
8. `args.estimate_with_discount` - Stored (line 87)
9. `args.exp_name` - Used for directory naming (line 88)

## Arguments used by KDMAEstimationDecisionSelector (parent class):
From the initialize_with_args method (lines 104-141):
1. `args.selector` - Used to determine use_drexel_format (line 105)
2. `args.case_file` - Used to read case base (lines 106-115)
3. `args.record_considered_decisions` - Stored (line 114)
4. `args.variant` - Stored (line 118)
5. `args.decision_verbose` - Used to set print_neighbors (line 119)
6. `args.insert_pauses` - Stored (line 120)
7. `args.ignore_relevance` - Used to set check_for_relevance (line 121)
8. `args.exp_name` - Used for directory creation (lines 122-126)
9. `args.weight_file` - Used to load weights (lines 128-139)
10. `args.uniform_weight` - Used to decide weight setup (line 136)
11. `args.training` - Stored (line 140)
12. `args.domain` - Stored (line 141)

## Summary:
The ins_online_learning.py script uses a subset of the available command-line arguments. Many arguments from the default parser are either:
1. Overridden with hardcoded values
2. Not used at all
3. Passed through to other components (like InsuranceOnlineApprovalSeeker)

The script adds its own specific arguments for the insurance online learning functionality, which are primarily used by the InsuranceOnlineApprovalSeeker class.