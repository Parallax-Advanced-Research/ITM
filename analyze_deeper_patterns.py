#!/usr/bin/env python3
"""
Deeper analysis of insurance data patterns to understand the actual relationship
between features and KDMA values
"""

import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder
# import matplotlib.pyplot as plt
# import seaborn as sns

def analyze_perfect_prediction_possibility():
    """Test if features can perfectly predict KDMA values."""
    
    print("=== TESTING PERFECT PREDICTION POSSIBILITY ===")
    
    # Load data
    df = pd.read_csv('/home/chris/itm_feature_insurance/data/insurance/train-50-50.csv')
    
    # Prepare features (exclude target and outcome columns)
    feature_cols = [
        'children_under_4', 'children_under_12', 'children_under_18', 'children_under_26',
        'employment_type', 'distance_dm_home_to_employer_hq', 'travel_location_known',
        'owns_rents', 'no_of_medical_visits_previous_year',
        'percent_family_members_with_chronic_condition',
        'percent_family_members_that_play_sports',
        'network_status', 'expense_type',
        'val1', 'val2', 'val3', 'val4'  # Include choice options
    ]
    
    # Prepare data
    X = df[feature_cols].copy()
    y = df['kdma_value']
    
    # Encode categorical variables
    le_dict = {}
    for col in X.columns:
        if X[col].dtype == 'object':
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))
            le_dict[col] = le
    
    # Test with Decision Tree (can capture perfect rules)
    dt = DecisionTreeClassifier(random_state=42, max_depth=None)
    dt.fit(X, y)
    dt_accuracy = accuracy_score(y, dt.predict(X))
    
    # Test with Random Forest
    rf = RandomForestClassifier(random_state=42, n_estimators=100)
    rf.fit(X, y)
    rf_accuracy = accuracy_score(y, rf.predict(X))
    
    print(f"Decision Tree accuracy: {dt_accuracy:.4f}")
    print(f"Random Forest accuracy: {rf_accuracy:.4f}")
    
    if dt_accuracy > 0.999:
        print("→ DETERMINISTIC: Features can perfectly predict KDMA values")
        print("→ XGBoost weights will plateau very quickly")
        
        # Show the decision tree rules
        from sklearn.tree import export_text
        tree_rules = export_text(dt, feature_names=feature_cols, max_depth=3)
        print("\nTop-level decision rules:")
        print(tree_rules[:500] + "...")
        
    elif dt_accuracy > 0.95:
        print("→ MOSTLY DETERMINISTIC: Features can predict KDMA with high accuracy")
        print("→ XGBoost weights will plateau moderately quickly")
    else:
        print("→ STOCHASTIC: Features cannot reliably predict KDMA values")
        print("→ XGBoost weights will continue improving over time")
    
    # Feature importance from Random Forest
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': rf.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"\nTop 10 most important features for predicting KDMA:")
    for idx, row in feature_importance.head(10).iterrows():
        print(f"  {row['feature']}: {row['importance']:.4f}")
    
    return dt_accuracy, rf_accuracy, feature_importance

def analyze_choice_patterns():
    """Analyze if customer choices follow predictable patterns."""
    
    print(f"\n=== CHOICE PATTERN ANALYSIS ===")
    
    df = pd.read_csv('/home/chris/itm_feature_insurance/data/insurance/train-50-50.csv')
    
    # Check if action_type correlates with demographic features
    print(f"Analyzing if demographics predict choices...")
    
    # Simple correlation analysis
    demo_cols = ['children_under_4', 'children_under_18', 'no_of_medical_visits_previous_year', 
                 'percent_family_members_with_chronic_condition']
    
    for col in demo_cols:
        if col in df.columns:
            # Group by KDMA value and see average demographics
            kdma_groups = df.groupby('kdma_value')[col].mean()
            print(f"\nAverage {col} by KDMA:")
            for kdma, avg_val in kdma_groups.items():
                print(f"  {kdma}: {avg_val:.2f}")
    
    # Check if choice values (val1-val4) predict KDMA
    val_cols = ['val1', 'val2', 'val3', 'val4']
    if all(col in df.columns for col in val_cols):
        print(f"\nAnalyzing choice option patterns...")
        
        # For each KDMA type, what values do they typically choose from?
        for kdma in ['low', 'high']:
            subset = df[df['kdma_value'] == kdma]
            chosen_values = subset['action_type'].values
            
            print(f"\nFor KDMA '{kdma}' customers:")
            print(f"  Chosen values range: {np.min(chosen_values)} to {np.max(chosen_values)}")
            print(f"  Average chosen value: {np.mean(chosen_values):.1f}")
            print(f"  Most common choices: {subset['action_type'].value_counts().head(3).to_dict()}")

def analyze_data_generation_hypothesis():
    """Test hypothesis about how this data was generated."""
    
    print(f"\n=== DATA GENERATION HYPOTHESIS ===")
    
    df = pd.read_csv('/home/chris/itm_feature_insurance/data/insurance/train-50-50.csv')
    
    # Hypothesis: Data is artificially balanced 50-50
    kdma_counts = df['kdma_value'].value_counts()
    print(f"KDMA distribution: {kdma_counts.to_dict()}")
    
    if abs(kdma_counts['low'] - kdma_counts['high']) < 100:
        print("→ ARTIFICIALLY BALANCED: Exactly 50-50 split suggests synthetic data")
        print("→ Real customer data would not have exact balance")
        print("→ This may indicate rule-based generation rather than real customer behavior")
    
    # Check if val1-val4 combinations repeat perfectly
    val_combinations = df[['val1', 'val2', 'val3', 'val4']].drop_duplicates()
    print(f"\nUnique val1-val4 combinations: {len(val_combinations)}")
    print(f"Total rows: {len(df)}")
    
    if len(val_combinations) < len(df) / 10:
        print("→ LIMITED CHOICE VARIETY: Suggests systematic generation")
    
    # Check for patterns in row ordering
    first_100 = df.head(100)['kdma_value'].value_counts()
    last_100 = df.tail(100)['kdma_value'].value_counts() 
    
    print(f"\nFirst 100 rows KDMA distribution: {first_100.to_dict()}")
    print(f"Last 100 rows KDMA distribution: {last_100.to_dict()}")

def main():
    print("Deep Insurance Data Pattern Analysis")
    print("="*50)
    
    # Test if perfect prediction is possible
    dt_acc, rf_acc, importance = analyze_perfect_prediction_possibility()
    
    # Analyze choice patterns
    analyze_choice_patterns()
    
    # Analyze data generation
    analyze_data_generation_hypothesis()
    
    # Final conclusions
    print(f"\n=== FINAL CONCLUSIONS ===")
    
    if dt_acc > 0.999:
        print(f"✓ DETERMINISTIC RELATIONSHIP CONFIRMED")
        print(f"  Features → KDMA mapping is learnable with {dt_acc:.1%} accuracy")
        print(f"  XGBoost weights will plateau quickly (50-200 iterations)")
        print(f"  Unlike medical domain with biological uncertainty")
        
    elif dt_acc > 0.90:
        print(f"✓ MOSTLY DETERMINISTIC RELATIONSHIP")
        print(f"  Features → KDMA mapping achievable with {dt_acc:.1%} accuracy") 
        print(f"  XGBoost weights will plateau moderately (200-500 iterations)")
        
    else:
        print(f"✗ STOCHASTIC RELATIONSHIP")
        print(f"  Features → KDMA mapping only {dt_acc:.1%} accurate")
        print(f"  XGBoost weights will continue improving like medical domain")
    
    print(f"\nUser's hypothesis: {'CONFIRMED' if dt_acc > 0.95 else 'PARTIALLY CONFIRMED' if dt_acc > 0.80 else 'REJECTED'}")
    print(f"Insurance data {'is' if dt_acc > 0.95 else 'may be'} more deterministic than medical data")

if __name__ == '__main__':
    main()