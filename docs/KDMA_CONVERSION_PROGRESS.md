# KDMA Conversion Work Progress

## Overview
This document tracks the progress of implementing KDMA (Key Decision-Making Attributes) conversion logic for the insurance domain to work with the domain-agnostic approach used in the ITM (In The Moment) system.

## Project Context
- **Repository**: ITM Feature Insurance  
- **Branch**: `feature_insurance`
- **Main Goal**: Convert insurance-specific KDMA formats to work with the internal domain framework
- **Key Challenge**: Bridge between insurance domain models (OpenAPI-generated) and internal domain logic without breaking legacy code

## Architecture Understanding

### Domain Structure
1. **`domain/insurance/models/`** - Auto-generated Pydantic models from OpenAPI schema (DO NOT MODIFY)
2. **`domain/internal/`** - Internal domain-agnostic framework (Decision, AlignmentTarget, Domain base class)  
3. **Current Issue**: Need conversion layer between insurance models and internal framework

### KDMA Format Requirements
- **Insurance Format**: String values ("low", "high") with KDMA names ("RISK", "CHOICE")
- **Internal Format**: Numeric values (0, 1) with lowercase names ("risk", "choice")
- **Target**: AlignmentTarget objects for KDMA estimation decision selector

## Work Completed ✅

### 1. Analysis Phase
- **Status**: ✅ COMPLETED
- **Files Analyzed**:
  - `components/decision_selector/kdma_estimation/kdma_estimation_decision_selector.py` - Domain-agnostic pattern to follow
  - `domain/internal/domain.py` - Base domain class
  - `domain/internal/target.py` - AlignmentTarget structure
  - `domain/insurance/models/` - Insurance-specific data models
  - Current insurance conversion logic in driver and approval seeker

### 2. Conversion Utility Creation
- **Status**: ✅ COMPLETED
- **New File**: `domain/insurance/conversion_utils.py`
- **New File**: `domain/insurance/__init__.py`

#### Key Functions Created:
```python
# Core conversion functions
convert_kdma_value(kdma_value_str: str) -> int  # "low"/"high" -> 0/1
normalize_kdma_name(kdma_name: str) -> str      # "RISK" -> "risk"

# AlignmentTarget creation
create_insurance_alignment_target(insurance_state: InsuranceState) -> AlignmentTarget
create_multi_kdma_alignment_target(kdma_data: Dict[str, str]) -> AlignmentTarget
create_alignment_target_from_csv_row(row_data: Dict[str, Any]) -> AlignmentTarget

# Utility functions
parse_kdma_args(kdma_args: List[str]) -> Dict[str, int]  # Command-line parsing
```

#### Testing Completed:
- ✅ String to numeric conversion ("low" -> 0, "high" -> 1)
- ✅ KDMA name normalization ("RISK" -> "risk", "CHOICE" -> "choice")
- ✅ Single KDMA target creation
- ✅ Multi-KDMA target creation (risk + choice)
- ✅ CSV data conversion
- ✅ Edge case handling (None values, parsing errors)

## Work In Progress 🚧

### 3. KDMA Name Standardization
- **Status**: 🚧 PENDING
- **Goal**: Ensure consistent lowercase naming throughout codebase
- **Target Files**: Various insurance-related components

### 4. Driver Integration
- **Status**: 🚧 PENDING  
- **Goal**: Update insurance driver to use conversion utilities
- **Target File**: `runner/insurance_driver.py` (lines 67-95)

## Work Planned 📋

### 5. Integration Testing
- **Goal**: Test conversion with real insurance data
- **Scope**: End-to-end KDMA conversion workflow

### 6. Approval Seeker Updates
- **Goal**: Update insurance online approval seeker to use standardized conversion
- **Target File**: `components/decision_selector/kdma_estimation/insurance_online_approval_seeker.py`

## Data Structure Analysis

### Current Insurance Data Format (CSV):
```csv
probe_id,probe,network_status,...,kdma,kdma_value
1,DEDUCTIBLE,TIER 1 NETWORK,...,RISK,low
2,DEDUCTIBLE,TIER 1 NETWORK,...,RISK,low  
3,DEDUCTIBLE,TIER 1 NETWORK,...,CHOICE,high
```

### Insurance State Model:
```python
class InsuranceState(BaseModel):
    kdma: Optional[StrictStr] = None          # "RISK" or "CHOICE"
    kdma_value: Optional[StrictStr] = None    # "low" or "high"
    # ... other insurance-specific fields
```

### Target AlignmentTarget Format:
```python
AlignmentTarget(
    name="insurance-risk",
    kdma_names=["risk"],
    values={"risk": 0},  # 0 for "low", 1 for "high"
    type=AlignmentTargetType.SCALAR
)
```

## Design Decisions Made

### 1. Utility Functions vs Custom Domain Class
- **Decision**: Use conversion utilities instead of creating InsuranceDomain class
- **Rationale**: 
  - Keeps separation between data models (`domain/insurance/models/`) and business logic (`domain/internal/`)
  - No redundancy with existing OpenAPI-generated models
  - Easier to maintain and test
  - Follows single responsibility principle

### 2. Preserve Legacy Architecture
- **Decision**: Extend existing patterns rather than replace them
- **Rationale**:
  - No breaking changes to existing code
  - Follows established domain-agnostic pattern from kdma_estimation_decision_selector.py
  - Insurance models remain as pure data structures

### 3. Support Both Single and Multi-KDMA Scenarios  
- **Decision**: Create functions for both current (single KDMA) and future (multi-KDMA) needs
- **Rationale**:
  - Current data has one KDMA per row
  - Future scenarios may need both risk and choice KDMAs
  - Flexible design for evolution

## Next Steps

1. **Update Insurance Driver** - Replace inline conversion with utility functions
2. **Standardize KDMA Names** - Ensure consistent lowercase naming  
3. **Integration Testing** - Test with real insurance data
4. **Update Approval Seeker** - Use standardized conversion logic
5. **Documentation** - Update any relevant API docs

## Success Criteria

### Functional Requirements ✅
- [x] Convert "low"/"high" to 0/1
- [x] Handle both "RISK" and "CHOICE" KDMAs
- [x] Create proper AlignmentTarget objects
- [x] Support single and multi-KDMA scenarios
- [x] Backward compatibility

### Non-Functional Requirements
- [ ] No breaking changes to existing code
- [ ] Clean separation of concerns
- [ ] Maintainable and testable code
- [ ] Proper error handling
- [x] Comprehensive documentation