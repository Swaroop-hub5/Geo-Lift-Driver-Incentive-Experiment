import pandas as pd
import numpy as np
import statsmodels.formula.api as smf # The industry standard for this

def calculate_did(df, treatment_group='Treatment', control_group='Control'):
    """
    Calculates DiD using OLS Regression to get P-Values.
    """
    # 1. Filter Data
    df = df[df['group'].isin([treatment_group, control_group])].copy()
    
    # 2. Encode Dummy Variables for Regression
    # is_treatment: 1 if Treatment Group, 0 if Control
    df['is_treatment'] = (df['group'] == treatment_group).astype(int)
    
    # is_post: 1 if Post-Intervention, 0 if Pre
    df['is_post'] = (df['period'] == 'Post-Intervention').astype(int)
    
    # 3. Run OLS Regression
    # Formula: supply_hours ~ is_treatment + is_post + (is_treatment * is_post)
    model = smf.ols("supply_hours ~ is_treatment * is_post", data=df).fit()
    
    # 4. Extract Results
    # The interaction term 'is_treatment:is_post' is the DiD Estimator
    did_estimator = model.params['is_treatment:is_post']
    p_value = model.pvalues['is_treatment:is_post']
    conf_int = model.conf_int().loc['is_treatment:is_post']
    
    # 5. Calculate Smart Lift (Relative to Counterfactual)
    # Get raw averages for the summary
    t_post_avg = df[(df['is_treatment']==1) & (df['is_post']==1)]['supply_hours'].mean()
    
    # Counterfactual = Actual Post - The Causal Impact
    counterfactual = t_post_avg - did_estimator
    
    lift_percent = did_estimator / counterfactual if counterfactual != 0 else 0.0

    results = {
        "did_absolute_impact": float(did_estimator),
        "lift_percent": float(lift_percent),
        "p_value": float(p_value),
        "is_significant": bool(p_value < 0.05),
        "conf_int_lower": float(conf_int[0]),
        "conf_int_upper": float(conf_int[1]),
        "model_summary": model.summary().as_text() # Optional: Full statistical report
    }
    
    return results