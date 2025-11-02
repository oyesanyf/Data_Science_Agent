"""
Comprehensive statistical inference and ANOVA tools.
25+ tools for t-tests, ANOVA, nonparametrics, effect sizes, diagnostics, etc.
"""
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from .ds_tools import ensure_display_fields

logger = logging.getLogger(__name__)

def _lib_missing(name: str) -> dict:
    return {
        "status": "failed",
        "error": f"Optional dependency '{name}' is not installed.",
        "hint": f"pip install {name}"
    }

# -------- Basic Parametric / Nonparametric --------
@ensure_display_fields
def ttest_ind_tool(x: str, y: str, equal_var: bool = True) -> dict:
    """Two-sample t-test on columns x vs y (independent)."""
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="ttest_ind", x=x, y=y, equal_var=equal_var)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def ttest_rel_tool(x: str, y: str) -> dict:
    """Paired t-test on columns x vs y (dependent)."""
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="ttest_rel", x=x, y=y)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def mannwhitney_tool(x: str, y: str, alternative: str = "two-sided") -> dict:
    """Mann–Whitney U (independent, nonparametric)."""
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="mannwhitney", x=x, y=y, alternative=alternative)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def wilcoxon_tool(x: str, y: str, alternative: str = "two-sided") -> dict:
    """Wilcoxon signed-rank (paired, nonparametric)."""
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="wilcoxon", x=x, y=y, alternative=alternative)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def kruskal_wallis_tool(columns: List[str]) -> dict:
    """Kruskal–Wallis H-test across multiple groups (nonparametric ANOVA)."""
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="kruskal", columns=columns)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# ----------------- ANOVA & Post-hoc ----------------
@ensure_display_fields
def anova_oneway_tool(target: str, group: str) -> dict:
    """One-way ANOVA of target by group."""
    try:
        import statsmodels.api as sm  # noqa
        import statsmodels.formula.api as smf  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="anova_oneway", target=target, group=group)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def anova_twoway_tool(target: str, factor_a: str, factor_b: str, interaction: bool = True) -> dict:
    """Two-way ANOVA with/without interaction."""
    try:
        import statsmodels.api as sm  # noqa
        import statsmodels.formula.api as smf  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="anova_twoway", target=target, factor_a=factor_a, factor_b=factor_b, interaction=interaction)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def tukey_hsd_tool(target: str, group: str, alpha: float = 0.05) -> dict:
    """Tukey HSD post-hoc comparisons following ANOVA."""
    try:
        import statsmodels.stats.multicomp as mc  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="tukey_hsd", target=target, group=group, alpha=alpha)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# --------------- Proportions & Contingency ----------
@ensure_display_fields
def chisq_independence_tool(cat_x: str, cat_y: str) -> dict:
    """Chi-square test of independence on two categorical columns."""
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="chisq_independence", x=cat_x, y=cat_y)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def proportions_ztest_tool(successes_col: str, nobs_col: str, prop: Optional[float] = None) -> dict:
    """One-/two-sample z-test for proportions. If 'prop' is provided, one-sample test."""
    try:
        import statsmodels.stats.proportion as smp  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="proportions_ztest", successes_col=successes_col, nobs_col=nobs_col, prop=prop)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def mcnemar_tool(a_both: str, b_both: str, continuity: bool = True) -> dict:
    """McNemar test for paired nominal data (requires 2x2 counts columns)."""
    try:
        import statsmodels.stats.contingency_tables as sct  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="mcnemar", a_both=a_both, b_both=b_both, continuity=continuity)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def cochran_q_tool(binary_columns: List[str]) -> dict:
    """Cochran's Q for k related samples (binary outcomes)."""
    try:
        import statsmodels.api as sm  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="cochran_q", columns=binary_columns)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# ----------------- Correlation Tests ----------------
@ensure_display_fields
def pearson_corr_tool(x: str, y: str) -> dict:
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="pearson", x=x, y=y)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def spearman_corr_tool(x: str, y: str) -> dict:
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="spearman", x=x, y=y)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def kendall_corr_tool(x: str, y: str) -> dict:
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="kendall", x=x, y=y)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# --------------- Normality & Variance Tests ----------
@ensure_display_fields
def shapiro_normality_tool(column: str) -> dict:
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="shapiro", column=column)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def anderson_darling_tool(column: str) -> dict:
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="anderson", column=column)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def jarque_bera_tool(column: str) -> dict:
    try:
        import statsmodels.stats.stattools as sst  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="jarque_bera", column=column)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def levene_homoskedasticity_tool(columns: List[str]) -> dict:
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="levene", columns=columns)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def bartlett_homoskedasticity_tool(columns: List[str]) -> dict:
    try:
        import scipy.stats as st  # noqa
    except Exception:
        return _lib_missing("scipy")
    try:
        from .ds_tools import stats
        return stats(mode="bartlett", columns=columns)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# ---------------- Effect Sizes & CI/Bootstrap --------
@ensure_display_fields
def cohens_d_tool(x: str, y: str, paired: bool = False) -> dict:
    """Effect size for mean differences."""
    try:
        from .ds_tools import stats
        return stats(mode="effect_size_cohens_d", x=x, y=y, paired=paired)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def hedges_g_tool(x: str, y: str, paired: bool = False) -> dict:
    try:
        from .ds_tools import stats
        return stats(mode="effect_size_hedges_g", x=x, y=y, paired=paired)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def eta_squared_tool(target: str, group: str) -> dict:
    """ANOVA effect size."""
    try:
        from .ds_tools import stats
        return stats(mode="eta_squared", target=target, group=group)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def omega_squared_tool(target: str, group: str) -> dict:
    try:
        from .ds_tools import stats
        return stats(mode="omega_squared", target=target, group=group)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def cliffs_delta_tool(x: str, y: str) -> dict:
    """Effect size for ordinal/nonparametric differences."""
    try:
        from .ds_tools import stats
        return stats(mode="cliffs_delta", x=x, y=y)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def ci_mean_tool(column: str, level: float = 0.95, bootstrap: bool = False, n_boot: int = 2000) -> dict:
    """Confidence interval for a mean (analytic or bootstrap)."""
    try:
        from .ds_tools import stats
        return stats(mode="ci_mean", column=column, level=level, bootstrap=bootstrap, n_boot=n_boot)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# ---------------- Power & Sample Size ----------------
@ensure_display_fields
def power_ttest_tool(effect_size: float, alpha: float = 0.05, power: Optional[float] = None, nobs: Optional[int] = None, alternative: str = "two-sided") -> dict:
    """Solve for one of: power or nobs, given effect size & alpha."""
    try:
        import statsmodels.stats.power as smp  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="power_ttest", effect_size=effect_size, alpha=alpha, power=power, nobs=nobs, alternative=alternative)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def power_anova_tool(k_groups: int, effect_size: float, alpha: float = 0.05, power: Optional[float] = None, nobs: Optional[int] = None) -> dict:
    """Power / sample size for one-way ANOVA."""
    try:
        import statsmodels.stats.power as smp  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="power_anova", k_groups=k_groups, effect_size=effect_size, alpha=alpha, power=power, nobs=nobs)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# ---------------- Regression Diagnostics --------------
@ensure_display_fields
def vif_tool(feature_columns: List[str]) -> dict:
    """Variance Inflation Factors (multicollinearity)."""
    try:
        import statsmodels.api as sm  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="vif", columns=feature_columns)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def breusch_pagan_tool(residuals_col: str, features: List[str]) -> dict:
    """Test for heteroscedasticity."""
    try:
        import statsmodels.stats.diagnostic as ssd  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="breusch_pagan", residuals_col=residuals_col, features=features)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def white_test_tool(residuals_col: str, features: List[str]) -> dict:
    """White's test for heteroscedasticity."""
    try:
        import statsmodels.stats.diagnostic as ssd  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="white_test", residuals_col=residuals_col, features=features)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def durbin_watson_tool(residuals_col: str) -> dict:
    """Autocorrelation in residuals."""
    try:
        import statsmodels.stats.stattools as sst  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="durbin_watson", residuals_col=residuals_col)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# --------------- Multiple-Testing Control -------------
@ensure_display_fields
def bonferroni_correction_tool(pvals_col: str, alpha: float = 0.05) -> dict:
    try:
        import statsmodels.stats.multitest as mt  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="bonferroni", pvals_col=pvals_col, alpha=alpha)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def benjamini_hochberg_fdr_tool(pvals_col: str, alpha: float = 0.05) -> dict:
    try:
        import statsmodels.stats.multitest as mt  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="bh_fdr", pvals_col=pvals_col, alpha=alpha)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# ---------------- Time Series Stationarity ------------
@ensure_display_fields
def adf_stationarity_tool(series: str, regression: str = "c") -> dict:
    """Augmented Dickey-Fuller test."""
    try:
        from statsmodels.tsa.stattools import adfuller  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="adf", series=series, regression=regression)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@ensure_display_fields
def kpss_stationarity_tool(series: str, regression: str = "c") -> dict:
    """KPSS stationarity test."""
    try:
        from statsmodels.tsa.stattools import kpss  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .ds_tools import stats
        return stats(mode="kpss", series=series, regression=regression)
    except Exception as e:
        return {"status": "failed", "error": str(e)}
