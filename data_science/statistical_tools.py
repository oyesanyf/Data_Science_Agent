"""
Advanced statistical analysis tools for ANOVA and inference testing.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional, List, Union
from scipy import stats
from scipy.stats import f_oneway, chi2_contingency, ttest_ind, ttest_rel, mannwhitneyu, kruskal
import warnings
from .ds_tools import ensure_display_fields, _load_dataframe, _get_workspace_dir
import json
from pathlib import Path
from google.genai import types

logger = logging.getLogger(__name__)

@ensure_display_fields
async def anova(
    target: str,
    categorical_vars: str = "",
    csv_path: str = "",
    alpha: str = "0.05",
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Perform ANOVA (Analysis of Variance) to test differences between groups.
    
    Args:
        target: Continuous target variable name
        categorical_vars: Comma-separated categorical variables to test
        csv_path: Path to CSV file (optional, uses session default)
        alpha: Significance level (default 0.05)
        tool_context: Tool context for state management
        
    Returns:
        ANOVA results with F-statistic, p-value, and interpretation
    """
    try:
        # Load data
        df = await _load_dataframe(csv_path, tool_context=tool_context)
        
        # Parse parameters
        alpha_float = float(alpha)
        cat_vars = [v.strip() for v in categorical_vars.split(",") if v.strip()]
        
        if not cat_vars:
            return {
                "status": "failed",
                "error": "No categorical variables specified",
                "message": "Please provide categorical_vars parameter"
            }
        
        if target not in df.columns:
            return {
                "status": "failed",
                "error": f"Target variable '{target}' not found",
                "available_columns": list(df.columns)
            }
        
        # Validate categorical variables
        missing_cats = [v for v in cat_vars if v not in df.columns]
        if missing_cats:
            return {
                "status": "failed",
                "error": f"Categorical variables not found: {missing_cats}",
                "available_columns": list(df.columns)
            }
        
        # Prepare data
        target_data = df[target].dropna()
        
        # Perform ANOVA for each categorical variable
        anova_results = {}
        
        for cat_var in cat_vars:
            try:
                # Get groups
                groups = []
                group_labels = []
                
                for group in df[cat_var].dropna().unique():
                    group_data = df[df[cat_var] == group][target].dropna()
                    if len(group_data) > 0:
                        groups.append(group_data)
                        group_labels.append(str(group))
                
                if len(groups) < 2:
                    anova_results[cat_var] = {
                        "status": "failed",
                        "error": f"Not enough groups in {cat_var}",
                        "groups_found": len(groups)
                    }
                    continue
                
                # Perform one-way ANOVA
                f_stat, p_value = f_oneway(*groups)
                
                # Calculate effect size (eta-squared)
                ss_between = sum(len(group) * (group.mean() - target_data.mean())**2 for group in groups)
                ss_total = sum((target_data - target_data.mean())**2)
                eta_squared = ss_between / ss_total if ss_total > 0 else 0
                
                # Interpret results
                is_significant = p_value < alpha_float
                effect_size = "small" if eta_squared < 0.01 else "medium" if eta_squared < 0.06 else "large"
                
                # Group statistics
                group_stats = {}
                for i, (group_data, label) in enumerate(zip(groups, group_labels)):
                    group_stats[label] = {
                        "n": len(group_data),
                        "mean": float(group_data.mean()),
                        "std": float(group_data.std()),
                        "min": float(group_data.min()),
                        "max": float(group_data.max())
                    }
                
                anova_results[cat_var] = {
                    "status": "success",
                    "f_statistic": float(f_stat),
                    "p_value": float(p_value),
                    "is_significant": is_significant,
                    "alpha": alpha_float,
                    "eta_squared": float(eta_squared),
                    "effect_size": effect_size,
                    "groups": len(groups),
                    "group_labels": group_labels,
                    "group_statistics": group_stats,
                    "interpretation": f"F({len(groups)-1}, {len(target_data)-len(groups)}) = {f_stat:.3f}, p = {p_value:.3f}. {'Significant' if is_significant else 'Not significant'} difference between groups (α = {alpha_float}). Effect size: {effect_size} (η² = {eta_squared:.3f})"
                }
                
            except Exception as e:
                anova_results[cat_var] = {
                    "status": "failed",
                    "error": f"ANOVA failed for {cat_var}: {str(e)}"
                }
        
        # Summary
        significant_vars = [var for var, result in anova_results.items() 
                          if result.get("status") == "success" and result.get("is_significant")]

        # Save to artifact
        if tool_context:
            try:
                reports_dir = _get_workspace_dir(tool_context, "reports")
                report_path = Path(reports_dir) / "anova_results.md"

                markdown_content = f"# ANOVA Results for {target}\n\n"
                for var, result in anova_results.items():
                    markdown_content += f"## Analysis for {var}\n"
                    if result['status'] == 'success':
                        markdown_content += f"- **Interpretation**: {result['interpretation']}\n"
                        markdown_content += f"- **P-value**: {result['p_value']:.4f}\n"
                        markdown_content += f"- **Effect Size (eta-squared)**: {result['eta_squared']:.4f} ({result['effect_size']})\n"
                    else:
                        markdown_content += f"- **Error**: {result['error']}\n"

                with open(report_path, "w") as f:
                    f.write(markdown_content)

                with open(report_path, "rb") as f:
                    await tool_context.save_artifact("anova_results.md", types.Part.from_bytes(f.read(), "text/markdown"))
            except Exception as e:
                logger.warning(f"Failed to save ANOVA artifact: {e}")

        
        return {
            "status": "success",
            "target_variable": target,
            "categorical_variables": cat_vars,
            "alpha": alpha_float,
            "results": anova_results,
            "significant_variables": significant_vars,
            "summary": f"ANOVA completed for {len(cat_vars)} variables. {len(significant_vars)} showed significant differences (p < {alpha_float}).",
            "recommendations": [
                f"Variables with significant differences: {', '.join(significant_vars)}" if significant_vars else "No significant differences found",
                "Consider post-hoc tests (Tukey's HSD) for pairwise comparisons",
                "Check assumptions: normality, homogeneity of variance",
                "Effect sizes help interpret practical significance"
            ]
        }
        
    except Exception as e:
        logger.error(f"ANOVA analysis failed: {e}")
        return {
            "status": "failed",
            "error": f"ANOVA analysis failed: {str(e)}"
        }

@ensure_display_fields
async def inference(
    test_type: str = "t_test",
    variable1: str = "",
    variable2: str = "",
    csv_path: str = "",
    alpha: str = "0.05",
    alternative: str = "two-sided",
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Perform statistical inference tests.
    
    Args:
        test_type: Type of test (t_test, chi2, mannwhitney, kruskal, correlation)
        variable1: First variable name
        variable2: Second variable name (for two-sample tests)
        csv_path: Path to CSV file
        alpha: Significance level
        alternative: Alternative hypothesis (two-sided, greater, less)
        tool_context: Tool context for state management
        
    Returns:
        Statistical test results with interpretation
    """
    try:
        # Load data
        df = await _load_dataframe(csv_path, tool_context=tool_context)
        alpha_float = float(alpha)
        
        # Validate variables
        if variable1 not in df.columns:
            return {
                "status": "failed",
                "error": f"Variable1 '{variable1}' not found",
                "available_columns": list(df.columns)
            }
        
        if variable2 and variable2 not in df.columns:
            return {
                "status": "failed",
                "error": f"Variable2 '{variable2}' not found",
                "available_columns": list(df.columns)
            }
        
        # Prepare data
        var1_data = df[variable1].dropna()
        
        if test_type == "t_test":
            if not variable2:
                return {
                    "status": "failed",
                    "error": "Two-sample t-test requires variable2"
                }
            
            var2_data = df[variable2].dropna()
            
            # Check if paired or independent
            is_paired = len(var1_data) == len(var2_data)
            
            if is_paired:
                # Paired t-test
                stat, p_value = ttest_rel(var1_data, var2_data, alternative=alternative)
                test_name = "Paired t-test"
            else:
                # Independent t-test
                stat, p_value = ttest_ind(var1_data, var2_data, alternative=alternative)
                test_name = "Independent t-test"
            
            # Calculate effect size (Cohen's d)
            pooled_std = np.sqrt(((len(var1_data) - 1) * var1_data.var() + 
                                 (len(var2_data) - 1) * var2_data.var()) / 
                                (len(var1_data) + len(var2_data) - 2))
            cohens_d = (var1_data.mean() - var2_data.mean()) / pooled_std if pooled_std > 0 else 0
            
            effect_size = "small" if abs(cohens_d) < 0.2 else "medium" if abs(cohens_d) < 0.8 else "large"
            
            result = {
                "test_name": test_name,
                "statistic": float(stat),
                "p_value": float(p_value),
                "is_significant": p_value < alpha_float,
                "cohens_d": float(cohens_d),
                "effect_size": effect_size,
                "n1": len(var1_data),
                "n2": len(var2_data),
                "mean1": float(var1_data.mean()),
                "mean2": float(var2_data.mean()),
                "std1": float(var1_data.std()),
                "std2": float(var2_data.std())
            }
            
        elif test_type == "chi2":
            if not variable2:
                return {
                    "status": "failed",
                    "error": "Chi-square test requires variable2"
                }
            
            # Create contingency table
            contingency_table = pd.crosstab(df[variable1], df[variable2])
            chi2_stat, p_value, dof, expected = chi2_contingency(contingency_table)
            
            # Calculate Cramér's V (effect size)
            n = contingency_table.sum().sum()
            cramers_v = np.sqrt(chi2_stat / (n * (min(contingency_table.shape) - 1)))
            
            effect_size = "small" if cramers_v < 0.1 else "medium" if cramers_v < 0.3 else "large"
            
            result = {
                "test_name": "Chi-square test of independence",
                "chi2_statistic": float(chi2_stat),
                "p_value": float(p_value),
                "degrees_of_freedom": int(dof),
                "is_significant": p_value < alpha_float,
                "cramers_v": float(cramers_v),
                "effect_size": effect_size,
                "contingency_table": contingency_table.to_dict(),
                "expected_frequencies": expected.tolist()
            }
            
        elif test_type == "mannwhitney":
            if not variable2:
                return {
                    "status": "failed",
                    "error": "Mann-Whitney U test requires variable2"
                }
            
            var2_data = df[variable2].dropna()
            stat, p_value = mannwhitneyu(var1_data, var2_data, alternative=alternative)
            
            # Calculate effect size (r)
            n1, n2 = len(var1_data), len(var2_data)
            r = 1 - (2 * stat) / (n1 * n2)
            
            effect_size = "small" if abs(r) < 0.1 else "medium" if abs(r) < 0.3 else "large"
            
            result = {
                "test_name": "Mann-Whitney U test",
                "u_statistic": float(stat),
                "p_value": float(p_value),
                "is_significant": p_value < alpha_float,
                "effect_size_r": float(r),
                "effect_size": effect_size,
                "n1": len(var1_data),
                "n2": len(var2_data),
                "median1": float(var1_data.median()),
                "median2": float(var2_data.median())
            }
            
        elif test_type == "kruskal":
            if not variable2:
                return {
                    "status": "failed",
                    "error": "Kruskal-Wallis test requires variable2"
                }
            
            # Get groups
            groups = []
            for group in df[variable2].dropna().unique():
                group_data = df[df[variable2] == group][variable1].dropna()
                if len(group_data) > 0:
                    groups.append(group_data)
            
            if len(groups) < 2:
                return {
                    "status": "failed",
                    "error": "Not enough groups for Kruskal-Wallis test"
                }
            
            stat, p_value = kruskal(*groups)
            
            result = {
                "test_name": "Kruskal-Wallis test",
                "h_statistic": float(stat),
                "p_value": float(p_value),
                "is_significant": p_value < alpha_float,
                "groups": len(groups),
                "total_n": sum(len(group) for group in groups)
            }
            
        elif test_type == "correlation":
            if not variable2:
                return {
                    "status": "failed",
                    "error": "Correlation test requires variable2"
                }
            
            var2_data = df[variable2].dropna()
            
            # Align data
            aligned_data = pd.DataFrame({
                variable1: var1_data,
                variable2: var2_data
            }).dropna()
            
            if len(aligned_data) < 3:
                return {
                    "status": "failed",
                    "error": "Not enough data for correlation test"
                }
            
            # Pearson correlation
            corr_coef, p_value = stats.pearsonr(aligned_data[variable1], aligned_data[variable2])
            
            # Spearman correlation
            spearman_coef, spearman_p = stats.spearmanr(aligned_data[variable1], aligned_data[variable2])
            
            effect_size = "small" if abs(corr_coef) < 0.1 else "medium" if abs(corr_coef) < 0.3 else "large"
            
            result = {
                "test_name": "Correlation test",
                "pearson_r": float(corr_coef),
                "pearson_p": float(p_value),
                "spearman_r": float(spearman_coef),
                "spearman_p": float(spearman_p),
                "is_significant": p_value < alpha_float,
                "effect_size": effect_size,
                "n": len(aligned_data),
                "interpretation": f"Pearson r = {corr_coef:.3f}, p = {p_value:.3f}. {'Significant' if p_value < alpha_float else 'Not significant'} {'positive' if corr_coef > 0 else 'negative'} correlation"
            }
            
        else:
            return {
                "status": "failed",
                "error": f"Unknown test type: {test_type}",
                "supported_tests": ["t_test", "chi2", "mannwhitney", "kruskal", "correlation"]
            }
        
        # Add interpretation
        result["interpretation"] = f"{result['test_name']}: {'Significant' if result['is_significant'] else 'Not significant'} (p = {result['p_value']:.3f}, α = {alpha_float})"

        # Save to artifact
        if tool_context:
            try:
                reports_dir = _get_workspace_dir(tool_context, "reports")
                report_path = Path(reports_dir) / "inference_results.md"

                markdown_content = f"# Inference Test Results: {test_type}\n\n"
                markdown_content += f"## {result['test_name']}\n"
                markdown_content += f"- **Interpretation**: {result['interpretation']}\n"
                markdown_content += f"- **P-value**: {result['p_value']:.4f}\n"
                if 'effect_size' in result:
                    markdown_content += f"- **Effect Size**: {result['effect_size']}\n"

                with open(report_path, "w") as f:
                    f.write(markdown_content)

                with open(report_path, "rb") as f:
                    await tool_context.save_artifact("inference_results.md", types.Part.from_bytes(f.read(), "text/markdown"))
            except Exception as e:
                logger.warning(f"Failed to save inference artifact: {e}")

        
        return {
            "status": "success",
            "test_type": test_type,
            "variables": [variable1, variable2] if variable2 else [variable1],
            "alpha": alpha_float,
            "alternative": alternative,
            "result": result,
            "recommendations": [
                f"Result: {'Significant' if result['is_significant'] else 'Not significant'} at α = {alpha_float}",
                f"Effect size: {result.get('effect_size', 'N/A')}",
                "Consider checking assumptions and effect size interpretation",
                "Report confidence intervals for better interpretation"
            ]
        }
        
    except Exception as e:
        logger.error(f"Inference test failed: {e}")
        return {
            "status": "failed",
            "error": f"Inference test failed: {str(e)}"
        }
