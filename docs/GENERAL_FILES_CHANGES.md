# Changes to General-Use Files (Requiring Justification)

## Overview
This document tracks all changes made to general-use/domain-agnostic files during the insurance domain KDMA conversion work. These changes need careful justification as they affect the broader codebase beyond the insurance domain.

## Files Modified

### 1. `ins_online_learning.py`
**Type**: Insurance-specific file ✅ (No justification needed)
**Changes**: Extensive modifications to support insurance domain
- Added insurance-specific argument parsing
- Added CSV scenario generation 
- Added insurance-specific imports and error handling

### 2. `tad.py` 
**Type**: 🚨 GENERAL-USE FILE (Needs Justification)
**Git Status**: Modified (M)

**Analysis Needed**: 
- [ ] **TODO**: Analyze what changes were made to this file
- [ ] **TODO**: Determine if changes are insurance-specific or domain-agnostic improvements
- [ ] **TODO**: Provide justification for any changes

**Questions to Answer**:
- What specific lines/functions were modified?
- Are the changes backward compatible?
- Do changes benefit other domains or only insurance?
- Could changes be moved to insurance-specific files instead?

### 3. `scripts/shared.py`
**Type**: 🚨 GENERAL-USE FILE (Needs Justification)  
**Git Status**: Modified (M)

**Analysis Needed**:
- [ ] **TODO**: Review changes to shared functionality
- [ ] **TODO**: Determine impact on other domains
- [ ] **TODO**: Justify additions to shared codebase

**Likely Changes** (based on ins_online_learning.py imports):
- Addition of `get_insurance_parser()` function
- Need to verify this doesn't conflict with existing parsers

### 4. `components/decision_selector/kdma_estimation/kdma_estimation_decision_selector.py`
**Type**: 🚨 GENERAL-USE FILE (Needs Justification)
**Git Status**: Modified (M)

**Analysis Needed**:
- [ ] **TODO**: Review changes to KDMA estimation logic
- [ ] **TODO**: Ensure changes are domain-agnostic improvements
- [ ] **TODO**: Verify backward compatibility for existing domains

**Potential Concerns**:
- This is core KDMA estimation logic used by multiple domains
- Changes here affect medical triage, military scenarios, etc.
- Must ensure changes are generalizable, not insurance-specific

### 5. `components/decision_selector/kdma_estimation/insurance_online_approval_seeker.py`
**Type**: Insurance-specific file ✅ (No justification needed)
**Changes**: Insurance domain-specific KDMA handling

## Analysis Framework

### For Each General-Use File, We Need:

#### 1. **Change Analysis**
```bash
git diff <file>  # See specific changes
git blame <file> # See when changes were made
```

#### 2. **Impact Assessment**  
- Does it break existing functionality?
- Does it change public APIs?
- Does it affect other domains?

#### 3. **Justification Categories**
- **Bug Fix**: Fixing existing issues
- **Domain-Agnostic Improvement**: Benefits all domains
- **Infrastructure**: Better abstractions/utilities
- **Performance**: Optimization that helps everyone
- **❌ Insurance-Specific**: Should be moved to insurance files

#### 4. **Backward Compatibility Check**
- Are existing function signatures preserved?
- Are default behaviors unchanged?
- Can existing domains continue working without modification?

## Detailed Analysis Results

### `tad.py` Changes
**Status**: ⏳ PENDING ANALYSIS

**Commands to Run**:
```bash
git diff tad.py
git show HEAD~1:tad.py > tad.py.old
diff tad.py.old tad.py
```

**Expected Findings**:
- Likely addition of `insurance_test()` function
- Need to verify it doesn't modify existing `api_test()` logic

### `scripts/shared.py` Changes  
**Status**: ⏳ PENDING ANALYSIS

**Commands to Run**:
```bash
git diff scripts/shared.py
grep -n "insurance" scripts/shared.py
```

**Expected Findings**:
- Addition of insurance-specific argument parser
- Need to ensure it's properly namespaced and doesn't conflict

### `kdma_estimation_decision_selector.py` Changes
**Status**: ⏳ PENDING ANALYSIS

**Key Questions**:
- Were any core algorithms modified?
- Are changes in domain-agnostic utility functions?
- Do changes improve the general framework or add insurance-specific logic?

## Justification Template

For each general-use file change:

```
### File: <filename>
**Change Type**: [Bug Fix | Domain-Agnostic Improvement | Infrastructure | Insurance-Specific]
**Justification**: 
- **Problem Solved**: What issue did this change address?
- **Scope**: Does this benefit other domains or just insurance?
- **Alternatives**: Could this have been done in insurance-specific files?
- **Backward Compatibility**: Are existing domains unaffected?
- **Risk Assessment**: What could break and how likely?

**Recommendation**: [APPROVE | MODIFY | REJECT]
```

## Action Items

### Immediate (Before Continuing Development)
1. [ ] Analyze actual changes in each general-use file
2. [ ] Document justification for each change
3. [ ] Identify any changes that should be moved to insurance-specific files
4. [ ] Test backward compatibility with existing domains

### Before Merge/PR
1. [ ] Prepare justification documentation for review
2. [ ] Ensure all general-use changes are truly beneficial to multiple domains
3. [ ] Move any insurance-specific logic to appropriate insurance files
4. [ ] Add tests to prevent regression in general-use functionality

## Risk Mitigation

### High-Risk Changes
- Modifications to core KDMA estimation algorithms
- Changes to shared argument parsing that could conflict
- Alterations to base Domain class behavior

### Medium-Risk Changes  
- Addition of new utility functions to shared files
- New optional parameters to existing functions
- Infrastructure improvements

### Low-Risk Changes
- Bug fixes with clear scope
- Addition of truly domain-agnostic utilities
- Performance improvements with no behavior changes

## Notes
- Insurance domain work should ideally be contained within `domain/insurance/`, `components/*/insurance*/`, and `runner/insurance*` files
- Any changes to general-use files should pass the "would this benefit medical triage domain too?" test
- When in doubt, prefer composition over modification of general-use files