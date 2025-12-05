import pandas as pd
import numpy as np

def calculate_did(df, treatment_group='Treatment', control_group='Control'):
    """
    Calculates Difference-in-Differences (DiD) Estimator.
    Flexible: Can accept custom group names for Placebo testing.
    """
    # Filter only relevant groups
    df = df[df['group'].isin([treatment_group, control_group])].copy()
    
    # Group by Period and Group
    summary = df.groupby(['group', 'period'])['supply_hours'].mean().reset_index()
    
    # Helper to safely extract values
    def get_val(grp, per):
        val = summary[(summary['group'] == grp) & (summary['period'] == per)]['supply_hours'].values
        return float(val[0]) if len(val) > 0 else 0.0

    t_post = get_val(treatment_group, 'Post-Intervention')
    t_pre = get_val(treatment_group, 'Pre-Intervention')
    c_post = get_val(control_group, 'Post-Intervention')
    c_pre = get_val(control_group, 'Pre-Intervention')
    
    # DiD Calculation
    treatment_diff = t_post - t_pre
    control_diff = c_post - c_pre
    did_estimator = treatment_diff - control_diff
    
    # Simple Lift % relative to pre-treatment baseline
    lift_percent = did_estimator / t_pre if t_pre != 0 else 0.0
    
    results = {
        "did_absolute_impact": float(did_estimator),
        "lift_percent": float(lift_percent),
        "treatment_pre_avg": float(t_pre),
        "treatment_post_avg": float(t_post),
        "control_pre_avg": float(c_pre),
        "control_post_avg": float(c_post)
    }
    
    return results