"""
Conversion utilities for bridging insurance domain models with internal domain models.

This module provides functions to convert insurance-specific data structures
(auto-generated Pydantic models) to internal domain objects like AlignmentTarget.
"""

from typing import Dict, Any, Optional, List, Union
from domain.internal import AlignmentTarget, AlignmentTargetType
from .models.insurance_state import InsuranceState


def convert_kdma_value(kdma_value_str: str) -> float:
    """
    Convert insurance KDMA string value to numeric format.
    
    Args:
        kdma_value_str: String value ("low", "high", or numeric string)
        
    Returns:
        float: Numeric value (0.0 for "low", 1.0 for "high", or parsed number)
    """
    if kdma_value_str is None:
        return 0.0  # Default to low
        
    kdma_value_lower = kdma_value_str.lower().strip()
    
    if kdma_value_lower == 'low':
        return 0.0
    elif kdma_value_lower == 'high':
        return 1.0
    else:
        # Try to parse as number if it's not low/high
        try:
            return float(kdma_value_str)
        except (ValueError, TypeError):
            return 0.0  # Default to low if we can't parse


def normalize_kdma_name(kdma_name: str) -> str:
    """
    Normalize KDMA names to lowercase standard format.
    
    Args:
        kdma_name: KDMA name in any case ("RISK", "risk", "CHOICE", "choice")
        
    Returns:
        str: Lowercase normalized name ("risk", "choice")
    """
    if kdma_name is None:
        return ""
    return kdma_name.lower().strip()


def create_insurance_alignment_target(
    insurance_state: InsuranceState, 
    target_name: Optional[str] = None
) -> AlignmentTarget:
    """
    Convert insurance state KDMA data to AlignmentTarget.
    
    For single KDMA scenarios, creates target with one KDMA.
    For future multi-KDMA scenarios, can be extended to handle both risk and choice.
    
    Args:
        insurance_state: InsuranceState containing KDMA data
        target_name: Optional custom name for the target
        
    Returns:
        AlignmentTarget: Properly formatted target for KDMA estimation
    """
    if not insurance_state or not insurance_state.kdma:
        # Fallback to default target
        return AlignmentTarget(
            name="insurance-default",
            kdma_names=["risk"],
            values={"risk": 0},
            type=AlignmentTargetType.SCALAR
        )
    
    # Get KDMA data from insurance state
    kdma_name = normalize_kdma_name(insurance_state.kdma)
    kdma_value = convert_kdma_value(insurance_state.kdma_value)
    
    # Create target name
    if target_name is None:
        target_name = f"insurance-{kdma_name}"
    
    return AlignmentTarget(
        name=target_name,
        kdma_names=[kdma_name],
        values={kdma_name: kdma_value},
        type=AlignmentTargetType.SCALAR
    )


def create_multi_kdma_alignment_target(
    kdma_data: Dict[str, str],
    target_name: Optional[str] = None
) -> AlignmentTarget:
    """
    Create AlignmentTarget with multiple KDMAs (risk and choice).
    
    This function is for scenarios where we have both risk and choice KDMA values,
    either from multiple insurance states or from a combined data structure.
    
    Args:
        kdma_data: Dictionary mapping KDMA names to string values
                  e.g., {"RISK": "low", "CHOICE": "high"}
        target_name: Optional custom name for the target
        
    Returns:
        AlignmentTarget: Target with multiple KDMAs
    """
    if not kdma_data:
        return create_insurance_alignment_target(None)
    
    # Convert all KDMA values
    kdma_names = []
    kdma_values = {}
    
    for kdma_name, kdma_value_str in kdma_data.items():
        normalized_name = normalize_kdma_name(kdma_name)
        numeric_value = convert_kdma_value(kdma_value_str)
        
        kdma_names.append(normalized_name)
        kdma_values[normalized_name] = numeric_value
    
    # Create target name
    if target_name is None:
        kdma_names_sorted = sorted(kdma_names)
        target_name = f"insurance-{'-'.join(kdma_names_sorted)}"
    
    return AlignmentTarget(
        name=target_name,
        kdma_names=kdma_names,
        values=kdma_values,
        type=AlignmentTargetType.SCALAR
    )


def create_alignment_target_from_csv_row(row_data: Dict[str, Any]) -> AlignmentTarget:
    """
    Create AlignmentTarget from CSV row data (as used in insurance training data).
    
    Args:
        row_data: Dictionary containing CSV row data with 'kdma' and 'kdma_value' keys
        
    Returns:
        AlignmentTarget: Properly formatted target
    """
    kdma_name = row_data.get('kdma', 'risk')
    kdma_value_str = row_data.get('kdma_value', 'low')
    
    normalized_name = normalize_kdma_name(kdma_name)
    numeric_value = convert_kdma_value(kdma_value_str)
    
    return AlignmentTarget(
        name=f"insurance-{normalized_name}",
        kdma_names=[normalized_name],
        values={normalized_name: numeric_value},
        type=AlignmentTargetType.SCALAR
    )


def extract_action_from_csv_row(row_data: Dict[str, Any]) -> str:
    """
    Extract action from CSV row, handling both old and new column names.
    
    Supports both 'action' (old format) and 'action_type' (new format) columns.
    
    Args:
        row_data: Dictionary containing CSV row data
        
    Returns:
        str: Action name, or 'unknown' if not found
    """
    # Try new format first, then old format, then default
    return (row_data.get('action_type') or 
            row_data.get('action') or 
            'unknown')


def extract_action_id_from_csv_row(row_data: Dict[str, Any]) -> str:
    """
    Extract action ID from CSV row, handling multiple possible column names.
    
    Args:
        row_data: Dictionary containing CSV row data
        
    Returns:
        str: Action ID or generated ID if not found
    """
    import uuid
    
    # Try various ID column names
    action_id = (row_data.get('action_id') or 
                 row_data.get('decision_id') or 
                 row_data.get('id') or 
                 str(uuid.uuid4()))
    
    return str(action_id)


def parse_kdma_args(kdma_args: List[str]) -> Dict[str, int]:
    """
    Parse command-line KDMA arguments into normalized format.
    
    Handles formats like:
    - ["risk=0", "choice=1"]
    - ["risk-0", "choice-1"] 
    - ["RISK=low", "CHOICE=high"]
    
    Args:
        kdma_args: List of KDMA argument strings
        
    Returns:
        Dict mapping normalized KDMA names to numeric values
    """
    kdma_dict = {}
    
    if not kdma_args:
        return kdma_dict
    
    for kdma_arg in kdma_args:
        # Handle both = and - separators
        if '=' in kdma_arg:
            parts = kdma_arg.split('=', 1)
        elif '-' in kdma_arg:
            parts = kdma_arg.split('-', 1)
        else:
            # No separator, assume it's just a KDMA name with default value
            parts = [kdma_arg, '0']
        
        if len(parts) == 2:
            kdma_name = normalize_kdma_name(parts[0])
            kdma_value = convert_kdma_value(parts[1])
            kdma_dict[kdma_name] = kdma_value
    
    return kdma_dict