# Insurance Domain Merge Plan

## Overview
This document outlines the plan to merge the insurance-specific implementations back into the main codebase, creating a unified system that supports both medical triage and insurance domains.

## Files to Merge

### 1. Online Learning Scripts
- **Original**: `online_learning.py`
- **Insurance**: `ins_online_learning.py`
- **Goal**: Single `online_learning.py` supporting both domains

### 2. Online Approval Seeker
- **Original**: `components/decision_selector/kdma_estimation/online_approval_seeker.py`
- **Insurance**: `components/decision_selector/kdma_estimation/insurance_online_approval_seeker.py`
- **Goal**: Single `online_approval_seeker.py` supporting both domains

## Key Differences Analysis

### Online Learning Scripts

#### 1. Parser and Imports
- Medical uses `get_default_parser()`, Insurance uses `get_insurance_parser()`
- Insurance adds `Domain` object and `pandas` for CSV processing
- Different driver imports: `TA3Driver` vs `InsuranceDriver`

#### 2. Scenario Generation
- Medical: YAML files from `.deprepos/itm-evaluation-server/`
- Insurance: CSV files with `create_insurance_scenario_ids()` function

#### 3. TAD Execution
- Medical: `tad.api_test()`
- Insurance: `tad.insurance_test()`

#### 4. Testing Features
- Insurance adds batch size handling
- Insurance has enhanced test output printing
- Insurance adds test interval for periodic testing

#### 5. Port Checking
- Medical checks TA3, ADEPT, and Soartech ports
- Insurance removes port checking

### Online Approval Seeker

#### 1. Class Names
- Medical: `OnlineApprovalSeeker`
- Insurance: `InsuranceOnlineApprovalSeeker`

#### 2. Missing Imports in Original
- Original missing: `make_approval_data_frame`, `SimpleWeightTrainer`, `BASIC_TRIAGE_CASE_TYPES`

#### 3. Missing Attributes in Original
- `last_approval`, `last_kdma_value`, `weight_settings`, `is_training`

#### 4. KDMA Handling
- Medical: Single KDMA with simple parsing
- Insurance: Dual KDMA system (risk/choice) with complex parsing

#### 5. Decision Selection
- Insurance passes alignment target from driver in case-based mode
- Insurance has enhanced KDMA extraction logic

#### 6. Line 117 Bug
- Original has `self.all_fields = all_fields` (undefined variable)
- Insurance has `self.all_fields = other_seeker.all_fields`

## Merge Strategy

### Phase 1: Domain Detection
Add domain detection based on:
- `session_type` parameter
- Presence of specific files (CSV vs YAML)
- Command line arguments

### Phase 2: Unified Parser
Create a unified parser that:
1. Includes all arguments from both versions
2. Conditionally requires certain arguments based on domain
3. Sets appropriate defaults for each domain

### Phase 3: Component Selection
Implement factory pattern for:
1. Driver selection (TA3Driver vs InsuranceDriver)
2. Approval seeker instantiation
3. TAD function selection

### Phase 4: Unified Online Approval Seeker
1. Fix missing imports and attributes in original
2. Add domain-aware KDMA parsing
3. Support both single and dual KDMA systems
4. Make alignment target passing consistent

### Phase 5: Testing and Validation
1. Test medical triage functionality (if test data available)
2. Test insurance functionality
3. Verify no regression in either domain

## Implementation Steps

### Step 1: Fix Online Approval Seeker Base Issues
1. Add missing imports
2. Add missing attributes with defaults
3. Fix line 117 bug
4. Add domain-agnostic KDMA parsing

### Step 2: Create Domain-Aware Online Learning
1. Add domain detection logic
2. Implement conditional imports
3. Create unified parser
4. Add domain-specific scenario generation
5. Add domain-specific TAD execution

### Step 3: Enhance Base Classes
1. Add batch processing support to base
2. Add enhanced testing output as option
3. Make port checking conditional

### Step 4: Remove Duplicate Files
1. Remove `ins_online_learning.py`
2. Remove `insurance_online_approval_seeker.py`
3. Update all imports

## First Implementation Task

**Fix the base `online_approval_seeker.py` to include missing functionality:**

1. Add missing imports:
   - `make_approval_data_frame` from weight_trainer
   - `SimpleWeightTrainer` from simple_weight_trainer
   - `BASIC_TRIAGE_CASE_TYPES` from triage_constants

2. Add missing instance attributes:
   - `self.last_approval = None`
   - `self.last_kdma_value = None`
   - `self.weight_settings = {}`
   - `self.is_training = False`

3. Fix the bug on line 117:
   - Change `self.all_fields = all_fields` to `self.all_fields = other_seeker.all_fields`

4. Make the seeker domain-agnostic:
   - Add flexible KDMA parsing that handles both single and dual KDMA systems
   - Make alignment target passing consistent in select method

This will create a solid foundation before merging the domain-specific logic.