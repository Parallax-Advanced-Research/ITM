#!/usr/bin/env python3
"""Utility for formatting probe features for readable output"""

def format_probe_features(probe, compact=True):
    """Format probe features for readable display
    
    Args:
        probe: The probe object to format
        compact: If True, group similar features and show summary stats
    
    Returns:
        String with formatted probe information
    """
    if not hasattr(probe, 'state'):
        return "No state information available"
    
    state = probe.state
    lines = []
    
    # Basic info (skip Probe ID since it's already shown)
    lines.append(f"Prompt: {getattr(probe, 'prompt', 'N/A')}")
    
    # KDMA info (most important)
    if hasattr(state, 'kdma') and hasattr(state, 'kdma_value'):
        lines.append(f"Target KDMA: {state.kdma}={state.kdma_value}")
    
    if compact:
        # Group children by age ranges - simplify to just total
        children_fields = ['children_under_4', 'children_under_12', 'children_under_18', 'children_under_26']
        total_children = 0
        for field in children_fields:
            if hasattr(state, field):
                count = getattr(state, field, 0)
                total_children += count
        
        if total_children > 0:
            lines.append(f"Children: {total_children}")
        else:
            lines.append("Children: None")
        
        # Key demographic/contextual info
        key_fields = [
            ('employment_type', 'Employment'),
            ('owns_rents', 'Housing'),
            ('network_status', 'Network'),
            ('expense_type', 'Expense Type')
        ]
        
        for field, label in key_fields:
            if hasattr(state, field):
                value = getattr(state, field, 'N/A')
                lines.append(f"{label}: {value}")
        
        # Health/risk indicators
        if hasattr(state, 'no_of_medical_visits_previous_year'):
            visits = getattr(state, 'no_of_medical_visits_previous_year', 0)
            lines.append(f"Medical visits (prev year): {visits}")
        
        if hasattr(state, 'percent_family_members_with_chronic_condition'):
            chronic = getattr(state, 'percent_family_members_with_chronic_condition', 0)
            # Data is stored as whole numbers (6 = 6%), so divide by 100 for percentage formatting
            lines.append(f"Family chronic conditions: {chronic/100:.1%}")
        
        if hasattr(state, 'percent_family_members_that_play_sports'):
            sports = getattr(state, 'percent_family_members_that_play_sports', 0)
            # Data is stored as whole numbers (13 = 13%), so divide by 100 for percentage formatting
            lines.append(f"Family plays sports: {sports/100:.1%}")
        
        # Deductible values (val1-val4) formatted as currency
        values = []
        for i in range(1, 5):
            field = f'val{i}'
            if hasattr(state, field):
                val = getattr(state, field, 0)
                if val != 0:
                    values.append(f"${val:,.0f}")
        
        if values:
            lines.append(f"Deductible options: {', '.join(values)}")
    
    else:
        # Show all features (verbose mode)
        for attr_name in dir(state):
            if not attr_name.startswith('_') and not callable(getattr(state, attr_name)):
                value = getattr(state, attr_name)
                lines.append(f"{attr_name}: {value}")
    
    return '\n'.join(lines)

def format_decision_info(decision):
    """Format decision information for readable display"""
    lines = []
    
    if hasattr(decision, 'value') and hasattr(decision.value, 'name'):
        lines.append(f"Action: {decision.value.name}")
    
    if hasattr(decision, 'kdma_map') and decision.kdma_map:
        kdma_strs = [f"{k}:{v}" for k, v in decision.kdma_map.items()]
        lines.append(f"KDMAs: {', '.join(kdma_strs)}")
    
    # Add analyzer metrics if available
    if hasattr(decision, 'metrics') and decision.metrics:
        metrics_strs = []
        for metric_name, metric in decision.metrics.items():
            if metric and hasattr(metric, 'value') and metric.value is not None:
                # Extract the actual value from the metric object
                if hasattr(metric.value, 'actual_instance'):
                    # DecisionExplanationsInnerParamsValue wrapper - extract the real value
                    value = metric.value.actual_instance
                else:
                    # Direct value
                    value = metric.value
                
                # Format the metric name and value nicely
                formatted_name = metric_name.replace('_', ' ').title()
                if isinstance(value, float):
                    metrics_strs.append(f"{formatted_name}: {value:.1f}")
                else:
                    metrics_strs.append(f"{formatted_name}: {value}")
        
        if metrics_strs:
            lines.append(f"Analyzer: {', '.join(metrics_strs)}")
    
    return ' | '.join(lines) if lines else "No decision info"