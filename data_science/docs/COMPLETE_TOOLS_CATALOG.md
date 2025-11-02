# 📚 Complete Tools Catalog - All 150+ Tools

**Comprehensive reference for all data science tools available in the agent, organized by workflow stage.**

---

## 📊 Tool Count Summary

| Category | Count | Description |
|----------|-------|-------------|
| **Help & Discovery** | 4 | Documentation and workflow guidance |
| **File Management** | 3 | File operations and dataset discovery |
| **Quick Overview** | 1 | Fast dataset preview |
| **Unstructured Data** | 7 | PDF, images, audio, email processing |
| **Analysis & Visualization** | 3 | EDA and charting |
| **Data Cleaning** | 14 | Cleaning, preprocessing, transformation |
| **Model Training** | 16 | Scikit-learn and gradient boosting models |
| **Model Evaluation** | 2 | Performance metrics and validation |
| **Model Explainability** | 1 | SHAP interpretability |
| **Export & Reporting** | 2 | PDF reports and documentation |
| **Grid Search & Tuning** | 2 | Hyperparameter optimization |
| **Clustering** | 5 | Unsupervised learning |
| **Statistical Analysis** | 6 | Descriptive and inferential statistics |
| **Statistical Inference** | 34 | Hypothesis testing, ANOVA, effect sizes |
| **Advanced Modeling** | 22 | Gradient boosting, interpretability, anomaly detection |
| **Text Processing** | 1 | TF-IDF features |
| **AutoML** | 5 | Automated machine learning |
| **Data Validation** | 2 | Great Expectations |
| **Experiment Tracking** | 4 | MLflow integration |
| **Responsible AI** | 2 | Fairness and bias detection |
| **Drift Detection** | 2 | Data and model drift |
| **Causal Inference** | 2 | DoWhy causal analysis |
| **Feature Engineering (Advanced)** | 2 | Automated feature synthesis |
| **Imbalanced Learning** | 2 | SMOTE and calibration |
| **Time Series** | 2 | Forecasting and backtesting |
| **Embeddings & Search** | 2 | Semantic search |
| **Data Versioning** | 2 | DVC integration |
| **Monitoring** | 2 | Production drift monitoring |
| **Fast Query & EDA** | 2 | DuckDB and Polars |
| **Deep Learning** | 3 | PyTorch neural networks |

**TOTAL: 150+ Tools**

---

## 1. Help & Discovery (4 tools)

### 1.1 `help()`
**Description:** Show this help with all 150+ tools organized by 9-stage data science workflow (EDA → Data Cleaning → Feature Engineering → Statistical Analysis → ML → Reports → Production → Unstructured Data). Use present_full_tool_menu() for LLM-generated, stage-aware tool recommendations.

**Example:**
```python
help()
help(command='train')
```

---

### 1.2 `sklearn_capabilities()`
**Description:** List all supported sklearn algorithms by category (classification, regression, clustering, etc).

**Example:**
```python
sklearn_capabilities()
```

---

### 1.3 `suggest_next_steps()`
**Description:** AI-powered suggestions for next analysis steps based on current dataset/results.

**Example:**
```python
suggest_next_steps(data_rows=1000, data_cols=15)
```

---

### 1.4 `execute_next_step()`
**Description:** Execute a numbered next step from the interactive menu (e.g., execute_next_step(step_number=1)).

**Example:**
```python
execute_next_step(step_number=2)
```

---

## 2. File Management (3 tools)

### 2.1 `list_data_files()`
**Description:** List all uploaded files in the .uploaded folder (supports pattern filtering).

**Example:**
```python
list_data_files(pattern='*.csv')
```

---

### 2.2 `save_uploaded_file()`
**Description:** Save uploaded CSV content to .uploaded directory and return file path.

**Example:**
```python
save_uploaded_file(filename='mydata.csv', content='col1,col2\\n1,2')
```

---

### 2.3 `discover_datasets()`
**Description:** SMART FILE DISCOVERY: Auto-find CSV/Parquet files with rich metadata (size, rows, columns, timestamps). Includes fuzzy search by name, file recommendations, and 'most recent' suggestions. Use when file path is unknown or robust_auto_clean_file() fails to find a file.

**Example:**
```python
discover_datasets()  # Find all datasets
discover_datasets(search_pattern='customer', include_stats='yes')  # Search by name
discover_datasets(include_stats='no', max_results=10)  # Quick search
```

---

## 3. Quick Overview (1 tool)

### 3.1 `describe()`
**Description:** Quick dataset overview: describe() + head() combined. Shows statistics (mean, std, quartiles) and first rows.

**Example:**
```python
describe(n_rows=5)  # Quick overview: describe() + head() combined
```

---

## 4. Unstructured Data Processing (7 tools)

### 4.1 `extract_text()`
**Description:** Extract text from PDFs, DOCX, images (OCR), audio (STT), emails (.eml/.mbox), JSON/XML. Outputs normalized JSONL.

**Example:**
```python
extract_text('research_paper.pdf')  # Extract from PDF
extract_text('scanned_doc.png', type_hint='image/png')  # OCR from image
```

---

### 4.2 `chunk_text()`
**Description:** Split extracted text into token-aware chunks with configurable overlap. Uses sentence boundaries or fixed-size windows.

**Example:**
```python
chunk_text('research_paper.pdf', max_tokens=800, overlap=120, by='sentence')
```

---

### 4.3 `embed_and_index()`
**Description:** Generate embeddings using sentence-transformers and create FAISS index for fast semantic search.

**Example:**
```python
embed_and_index('research_paper.pdf', model='all-MiniLM-L6-v2')
```

---

### 4.4 `semantic_search()`
**Description:** Search by meaning (not keywords) using FAISS. Returns top-k similar chunks with distances.

**Example:**
```python
semantic_search('machine learning algorithms', k=10)
semantic_search('query', file_id='paper.pdf', filter_json='{"page": 5}')
```

---

### 4.5 `summarize_chunks()`
**Description:** LLM-powered summarization using map-reduce strategy. Summarizes each chunk then combines results.

**Example:**
```python
summarize_chunks('contract.pdf', mode='map-reduce', max_chunks=50)
```

---

### 4.6 `classify_text()`
**Description:** Ham/spam or custom text classification. Supports TF-IDF+NaiveBayes (fast) or LLM zero-shot (flexible).

**Example:**
```python
classify_text('emails.mbox', target='spam', strategy='tfidf-sklearn')  # Ham/spam
classify_text('reviews.csv', target='sentiment', label_set=['positive', 'negative'], strategy='llm')
```

---

### 4.7 `ingest_mailbox()`
**Description:** Parse .eml/.mbox files into structured CSV with columns: from, to, subject, date, body.

**Example:**
```python
ingest_mailbox('support_emails.mbox', split='per-message')
```

---

## 5. Analysis & Visualization (3 tools)

### 5.1 `analyze_dataset()`
**Description:** Comprehensive EDA: schema, statistics, correlations, outliers, PCA, clustering; saves plots.

**Example:**
```python
analyze_dataset(csv_path='tips.csv', sample_rows=10)
```

---

### 5.2 `plot()`
**Description:** Automatically generate 8 insightful charts (distributions, heatmap, time series, boxplots, scatter).

**Example:**
```python
plot(csv_path='tips.csv', max_charts=8)
```

---

### 5.3 `auto_analyze_and_model()`
**Description:** Smart workflow: EDA + automatic baseline model training if target detected.

**Example:**
```python
auto_analyze_and_model(csv_path='tips.csv', target='tip')
```

---

## 6. Data Cleaning & Preprocessing (14 tools)

### 6.1 `clean()`
**Description:** Complete data cleaning: standardize columns, remove duplicates/outliers, handle missing data, type inference.

**Example:**
```python
clean(csv_path='tips.csv', outlier_zscore_threshold=3.5, drop_duplicates=True)
```

---

### 6.2 `robust_auto_clean_file()`
**Description:** ADVANCED file-based cleaner with INTELLIGENT IMPUTATION: Auto-selects best imputation strategy per column (KNN for correlated data, Iterative ML for complex patterns, Median/Mode for simple cases). Also: outlier capping (IQR), type inference, header repair, stacked metadata detection (brain_networks.csv style), duplicate header cleanup, delimiter/encoding detection. Returns cleaned CSV/Parquet + imputation confidence scores.

**Example:**
```python
robust_auto_clean_file()  # Uses uploaded file automatically
robust_auto_clean_file(cap_outliers='yes', impute_missing='yes', drop_duplicate_rows='yes')
```

---

### 6.3 `detect_metadata_rows()`
**Description:** METADATA DETECTOR: Analyze CSV structure to detect stacked metadata/header rows (common in scientific datasets). Returns data start row, suggested headers, and detailed analysis.

**Example:**
```python
detect_metadata_rows(csv_path='brain_networks.csv')  # Analyze for stacked headers
detect_metadata_rows(csv_path='genomics.csv', max_rows_to_check=8)
```

---

### 6.4 `preview_metadata_structure()`
**Description:** PREVIEW: Show first N rows of CSV with structure analysis (numeric vs text columns). Useful before cleaning mixed-format datasets.

**Example:**
```python
preview_metadata_structure(csv_path='mixed_data.csv', rows=15)  # Preview first 15 rows
```

---

### 6.5 `auto_clean_data()`
**Description:** AutoGluon-powered quick data cleaning: handle missing values, outliers, type conversion.

**Example:**
```python
auto_clean_data(csv_path='messy_data.csv')
```

---

### 6.6 `scale_data()`
**Description:** Apply numeric scaling (StandardScaler, MinMaxScaler, RobustScaler) and save scaled CSV.

**Example:**
```python
scale_data(scaler='StandardScaler', csv_path='num.csv')
```

---

### 6.7 `encode_data()`
**Description:** One-hot encode categorical columns and save encoded CSV.

**Example:**
```python
encode_data(csv_path='tips.csv')
```

---

### 6.8 `expand_features()`
**Description:** Create polynomial or interaction features and save expanded CSV.

**Example:**
```python
expand_features(method='polynomial', degree=2, csv_path='num.csv')
```

---

### 6.9 `impute_simple()`
**Description:** Fill missing values with median (numeric) or mode (categorical); save imputed CSV.

**Example:**
```python
impute_simple(csv_path='missing.csv', strategy='median')
```

---

### 6.10 `impute_knn()`
**Description:** KNN imputation for missing numeric values; save imputed CSV.

**Example:**
```python
impute_knn(n_neighbors=5, csv_path='missing.csv')
```

---

### 6.11 `impute_iterative()`
**Description:** Iterative imputer (uses other features to predict missing values); save CSV.

**Example:**
```python
impute_iterative(csv_path='missing.csv', max_iter=10)
```

---

### 6.12 `select_features()`
**Description:** SelectKBest feature selection (chi2 for classification, f_regression for regression).

**Example:**
```python
select_features(target='smoker', k=10, csv_path='tips.csv')
```

---

### 6.13 `recursive_select()`
**Description:** Recursive Feature Elimination with Cross-Validation (RFECV).

**Example:**
```python
recursive_select(target='smoker', csv_path='tips.csv')
```

---

### 6.14 `sequential_select()`
**Description:** Sequential Feature Selection (forward or backward).

**Example:**
```python
sequential_select(target='smoker', direction='forward', n_features=8, csv_path='tips.csv')
```

---

## 7. Model Training & Prediction (16 tools)

### 7.1 `recommend_model()`
**Description:** AI-powered model recommendation: Get LLM-suggested TOP 3 models based on dataset characteristics (size, target distribution, features).

**Example:**
```python
recommend_model(target='price', csv_path='housing.csv')
```

---

### 7.2 `train()`
**Description:** Generic smart training (auto-detects classification vs regression, uses smart defaults).

**Example:**
```python
train(target='tip', csv_path='tips.csv', task='regression')
```

---

### 7.3 `train_baseline_model()`
**Description:** Quick baseline with preprocessing pipeline (impute/encode/scale) + LogisticRegression/Ridge.

**Example:**
```python
train_baseline_model(target='smoker', csv_path='tips.csv')
```

---

### 7.4 `train_classifier()`
**Description:** Train any sklearn classifier (LogisticRegression, RandomForest, GradientBoosting, SVC, etc).

**Example:**
```python
train_classifier(target='smoker', model='sklearn.ensemble.RandomForestClassifier', csv_path='tips.csv')
```

---

### 7.5 `train_regressor()`
**Description:** Train any sklearn regressor (Ridge, RandomForest, GradientBoosting, SVR, etc).

**Example:**
```python
train_regressor(target='tip', model='sklearn.ensemble.GradientBoostingRegressor', csv_path='tips.csv')
```

---

### 7.6 `train_decision_tree()`
**Description:** Train interpretable decision tree model with automatic tree visualization (PNG diagram saved to .plot folder).

**Example:**
```python
train_decision_tree(target='species', max_depth=5, csv_path='iris.csv')
```

---

### 7.7 `train_knn()`
**Description:** Train K-Nearest Neighbors (KNN) classifier or regressor with auto task detection.

**Example:**
```python
train_knn(target='species', n_neighbors=5, csv_path='iris.csv')
```

---

### 7.8 `train_naive_bayes()`
**Description:** Train Naive Bayes classifier (fast, works well for text and categorical data).

**Example:**
```python
train_naive_bayes(target='spam', csv_path='emails.csv')
```

---

### 7.9 `train_svm()`
**Description:** Train Support Vector Machine (SVM) for classification or regression with RBF kernel.

**Example:**
```python
train_svm(target='category', kernel='rbf', C=1.0, csv_path='data.csv')
```

---

### 7.10 `classify()`
**Description:** Train classification baseline for given target (auto-preprocessing, fast results).

**Example:**
```python
classify(target='smoker', csv_path='tips.csv')
```

---

### 7.11 `predict()`
**Description:** Train model and return comprehensive metrics for any target (auto task detection).

**Example:**
```python
predict(target='tip', csv_path='tips.csv')
```

---

### 7.12 `ensemble()`
**Description:** Multi-model ensemble using voting (soft/hard) - combines predictions from multiple algorithms. Now loads existing models first before training new ones.

**Example:**
```python
ensemble(target='species', models=['sklearn.linear_model.LogisticRegression', 'sklearn.ensemble.RandomForestClassifier'])
```

---

### 7.13 `load_model()`
**Description:** Load a saved model from .models folder by filename (returns model object for predictions).

**Example:**
```python
load_model(model_path='models/housing/price_model.joblib')
```

---

### 7.14 `load_existing_models()`
**Description:** Load all existing trained models for a dataset. Finds and loads all .joblib models in the models folder, used by ensemble() to avoid retraining.

**Example:**
```python
load_existing_models()
```

---

### 7.15 `apply_pca()`
**Description:** Principal Component Analysis for dimensionality reduction.

**Example:**
```python
apply_pca(n_components=2, csv_path='high_dim.csv')
```

---

### 7.16 `train_lightgbm_classifier()`
**Description:** Train LightGBM classifier (gradient boosting, fast, handles categorical features).

**Example:**
```python
train_lightgbm_classifier(target='churn', csv_path='customers.csv')
```

---

## 8. Model Evaluation (2 tools)

### 8.1 `evaluate()`
**Description:** Cross-validated model evaluation with any sklearn estimator.

**Example:**
```python
evaluate(target='smoker', model='sklearn.linear_model.LogisticRegression', csv_path='tips.csv')
```

---

### 8.2 `accuracy()`
**Description:** Comprehensive accuracy assessment: train/test split, K-fold CV, bootstrap, learning curves, confusion matrix.

**Example:**
```python
accuracy(target='species', model='sklearn.ensemble.RandomForestClassifier', cv_folds=5, bootstrap_samples=100)
```

---

## 9. Model Explainability (1 tool)

### 9.1 `explain_model()`
**Description:** SHAP explainability: feature importance, summary plots, waterfall plots, dependence plots, force plots - interpret model predictions.

**Example:**
```python
explain_model(target='tip', model='sklearn.ensemble.GradientBoostingRegressor', csv_path='tips.csv')
```

---

## 10. Export & Reporting (2 tools)

### 10.1 `export()`
**Description:** Generate comprehensive PDF report with executive summary, dataset info, all plots/charts, model results, and recommendations - saves to .export folder.

**Example:**
```python
export(title='Housing Analysis Report', summary='Comprehensive analysis of 10k housing records')
```

---

### 10.2 `export_executive_report()`
**Description:** AI-powered executive report with 6 sections: Problem Framing, Data Overview, Insights, Methodology, Results, Conclusion. Includes ALL charts + LLM-generated business insights.

**Example:**
```python
export_executive_report(project_title='Sales Forecasting', business_problem='Predict quarterly sales', target_variable='revenue', csv_path='sales.csv')
```

---

## 11. Grid Search & Tuning (2 tools)

### 11.1 `grid_search()`
**Description:** GridSearchCV hyperparameter tuning for any sklearn model with custom parameter grid.

**Example:**
```python
grid_search(target='smoker', model='sklearn.linear_model.LogisticRegression', param_grid={'C':[0.1,1,10]}, csv_path='tips.csv')
```

---

### 11.2 `split_data()`
**Description:** Train/test split by target column; saves train.csv and test.csv separately.

**Example:**
```python
split_data(target='smoker', test_size=0.2, csv_path='tips.csv')
```

---

## 12. Clustering (5 tools)

### 12.1 `smart_cluster()`
**Description:** AI-powered clustering: Auto-selects best algorithm (KMeans/DBSCAN/Hierarchical), determines optimal clusters, generates visualizations + LLM insights.

**Example:**
```python
smart_cluster(csv_path='customers.csv', max_clusters=10)
```

---

### 12.2 `kmeans_cluster()`
**Description:** K-Means clustering on numeric features; returns cluster assignments and centroids.

**Example:**
```python
kmeans_cluster(n_clusters=3, csv_path='tips.csv')
```

---

### 12.3 `dbscan_cluster()`
**Description:** Density-based clustering (DBSCAN) for arbitrary-shaped clusters; handles noise.

**Example:**
```python
dbscan_cluster(eps=0.5, min_samples=5, csv_path='num.csv')
```

---

### 12.4 `hierarchical_cluster()`
**Description:** Agglomerative hierarchical clustering with linkage options (ward, complete, average).

**Example:**
```python
hierarchical_cluster(n_clusters=4, linkage='ward', csv_path='num.csv')
```

---

### 12.5 `isolation_forest_train()`
**Description:** Anomaly detection using Isolation Forest (tree-based outlier detection).

**Example:**
```python
isolation_forest_train(contamination=0.1, csv_path='num.csv')
```

---

## 13. Statistical Analysis (6 tools)

### 13.1 `stats()`
**Description:** AI-powered statistical analysis: descriptive stats, normality tests, correlations, ANOVA, outlier detection, LLM insights.

**Example:**
```python
stats(csv_path='tips.csv')
```

---

### 13.2 `anomaly()`
**Description:** Multi-method anomaly detection: Isolation Forest, LOF, Z-Score, IQR, One-Class SVM + AI explanations.

**Example:**
```python
anomaly(csv_path='tips.csv', contamination=0.05, methods=['isolation_forest', 'lof', 'zscore'])
```

---

### 13.3 `anova()`
**Description:** Perform ANOVA (Analysis of Variance) to test differences between groups with effect sizes and interpretations.

**Example:**
```python
anova(dependent_var='score', independent_var='treatment', csv_path='experiment.csv')
```

---

### 13.4 `inference()`
**Description:** Perform statistical inference tests (t-tests, chi-square, Mann-Whitney U, Kruskal-Wallis, correlation tests) with effect sizes.

**Example:**
```python
inference(test_type='ttest', column1='group_a', column2='group_b', csv_path='data.csv')
```

---

### 13.5 `present_full_tool_menu()`
**Description:** LLM-generated comprehensive tool menu organized by data science stages. Shows all 150+ tools with stage-aware recommendations and smart defaults.

**Example:**
```python
present_full_tool_menu()
```

---

### 13.6 `route_user_intent()`
**Description:** Execute any tool directly with smart defaults. Example: route_user_intent(action='train_classifier', params={'target': 'label'}).

**Example:**
```python
route_user_intent(action='train_classifier', params={'target': 'label'})
```

---

## 14. Statistical Inference & ANOVA Tools (34 tools)

### 14.1 `ttest_ind_tool()`
**Description:** Two-sample t-test for independent groups (parametric test for comparing means).

---

### 14.2 `ttest_rel_tool()`
**Description:** Paired t-test for dependent groups (parametric test for comparing paired samples).

---

### 14.3 `mannwhitney_tool()`
**Description:** Mann-Whitney U test (nonparametric test for independent groups).

---

### 14.4 `wilcoxon_tool()`
**Description:** Wilcoxon signed-rank test (nonparametric test for paired samples).

---

### 14.5 `kruskal_wallis_tool()`
**Description:** Kruskal-Wallis H-test (nonparametric ANOVA for multiple groups).

---

### 14.6 `anova_oneway_tool()`
**Description:** One-way ANOVA to test differences between multiple groups.

---

### 14.7 `anova_twoway_tool()`
**Description:** Two-way ANOVA with/without interaction effects.

---

### 14.8 `tukey_hsd_tool()`
**Description:** Tukey HSD post-hoc comparisons following ANOVA.

---

### 14.9 `chisq_independence_tool()`
**Description:** Chi-square test of independence for categorical variables.

---

### 14.10 `proportions_ztest_tool()`
**Description:** Z-test for proportions (one-sample or two-sample).

---

### 14.11 `mcnemar_tool()`
**Description:** McNemar test for paired nominal data (2x2 contingency).

---

### 14.12 `cochran_q_tool()`
**Description:** Cochran's Q test for k related samples (binary outcomes).

---

### 14.13 `pearson_corr_tool()`
**Description:** Pearson correlation coefficient (linear relationship).

---

### 14.14 `spearman_corr_tool()`
**Description:** Spearman rank correlation (monotonic relationship).

---

### 14.15 `kendall_corr_tool()`
**Description:** Kendall's tau correlation (rank-based).

---

### 14.16 `shapiro_normality_tool()`
**Description:** Shapiro-Wilk test for normality (small samples).

---

### 14.17 `anderson_darling_tool()`
**Description:** Anderson-Darling test for normality (larger samples).

---

### 14.18 `jarque_bera_tool()`
**Description:** Jarque-Bera test for normality (based on skewness/kurtosis).

---

### 14.19 `levene_homoskedasticity_tool()`
**Description:** Levene test for equal variances (homoscedasticity).

---

### 14.20 `bartlett_homoskedasticity_tool()`
**Description:** Bartlett test for equal variances (normal data).

---

### 14.21 `cohens_d_tool()`
**Description:** Cohen's d effect size for mean differences.

---

### 14.22 `hedges_g_tool()`
**Description:** Hedges' g effect size (bias-corrected Cohen's d).

---

### 14.23 `eta_squared_tool()`
**Description:** Eta-squared effect size for ANOVA.

---

### 14.24 `omega_squared_tool()`
**Description:** Omega-squared effect size for ANOVA (less biased).

---

### 14.25 `cliffs_delta_tool()`
**Description:** Cliff's Delta effect size for nonparametric differences.

---

### 14.26 `ci_mean_tool()`
**Description:** Confidence interval for mean (analytic or bootstrap).

---

### 14.27 `power_ttest_tool()`
**Description:** Power analysis for t-tests (sample size or power calculation).

---

### 14.28 `power_anova_tool()`
**Description:** Power analysis for ANOVA (sample size or power calculation).

---

### 14.29 `vif_tool()`
**Description:** Variance Inflation Factors (multicollinearity detection).

---

### 14.30 `breusch_pagan_tool()`
**Description:** Breusch-Pagan test for heteroscedasticity.

---

### 14.31 `white_test_tool()`
**Description:** White's test for heteroscedasticity.

---

### 14.32 `durbin_watson_tool()`
**Description:** Durbin-Watson test for autocorrelation in residuals.

---

### 14.33 `bonferroni_correction_tool()`
**Description:** Bonferroni correction for multiple comparisons.

---

### 14.34 `benjamini_hochberg_fdr_tool()`
**Description:** Benjamini-Hochberg FDR control for multiple comparisons.

---

### 14.35 `adf_stationarity_tool()`
**Description:** Augmented Dickey-Fuller test for time series stationarity.

---

### 14.36 `kpss_stationarity_tool()`
**Description:** KPSS test for time series stationarity.

---

## 15. Advanced Modeling Tools (22 tools)

### 15.1 `train_xgboost_classifier()`
**Description:** Train XGBoost classifier (gradient boosting, high performance).

**Example:**
```python
train_xgboost_classifier(target='fraud', csv_path='transactions.csv')
```

---

### 15.2 `train_catboost_classifier()`
**Description:** Train CatBoost classifier (gradient boosting, handles categorical features natively).

**Example:**
```python
train_catboost_classifier(target='churn', csv_path='customers.csv')
```

---

### 15.3 `permutation_importance_tool()`
**Description:** Permutation importance for model interpretability.

---

### 15.4 `partial_dependence_tool()`
**Description:** Partial dependence plots for feature effects.

---

### 15.5 `ice_plot_tool()`
**Description:** Individual Conditional Expectation (ICE) plots.

---

### 15.6 `shap_interaction_values_tool()`
**Description:** SHAP interaction values for feature interactions.

---

### 15.7 `lime_explain_tool()`
**Description:** LIME (Local Interpretable Model-agnostic Explanations).

---

### 15.8 `smote_rebalance_tool()`
**Description:** SMOTE (Synthetic Minority Oversampling) for imbalanced datasets.

---

### 15.9 `threshold_tune_tool()`
**Description:** Threshold tuning for classification models.

---

### 15.10 `cost_sensitive_learning_tool()`
**Description:** Cost-sensitive learning for imbalanced datasets.

---

### 15.11 `target_encode_tool()`
**Description:** Target encoding for categorical variables.

---

### 15.12 `leakage_check_tool()`
**Description:** Data leakage detection in features.

---

### 15.13 `lof_anomaly_tool()`
**Description:** Local Outlier Factor (LOF) anomaly detection.

---

### 15.14 `oneclass_svm_anomaly_tool()`
**Description:** One-Class SVM anomaly detection.

---

### 15.15 `arima_forecast_tool()`
**Description:** ARIMA time series forecasting.

---

### 15.16 `sarimax_forecast_tool()`
**Description:** SARIMAX time series forecasting with seasonality.

---

### 15.17 `lda_topic_model_tool()`
**Description:** Latent Dirichlet Allocation (LDA) topic modeling.

---

### 15.18 `spacy_ner_tool()`
**Description:** SpaCy Named Entity Recognition (NER).

---

### 15.19 `sentiment_vader_tool()`
**Description:** VADER sentiment analysis.

---

### 15.20 `association_rules_tool()`
**Description:** Association rules mining (market basket analysis).

---

### 15.21 `export_onnx_tool()`
**Description:** Export model to ONNX format for deployment.

---

### 15.22 `onnx_runtime_infer_tool()`
**Description:** ONNX runtime inference for deployed models.

---

## 16. Text Processing (1 tool)

### 16.1 `text_to_features()`
**Description:** Convert text column to TF-IDF features (suitable for ML models).

**Example:**
```python
text_to_features(text_col='review', max_features=100, csv_path='reviews.csv')
```

---

## 17. AutoML (5 tools)

### 17.1 `smart_autogluon_automl()`
**Description:** AutoML with smart chunking for large datasets: Automatically trains/ensembles 10+ algorithms, handles memory limits.

**Example:**
```python
smart_autogluon_automl(target='price', time_limit=120, presets='best_quality')
```

---

### 17.2 `smart_autogluon_timeseries()`
**Description:** Time series AutoML: Auto-detects seasonality, trends, handles missing values, forecasts future values.

**Example:**
```python
smart_autogluon_timeseries(target='sales', datetime_col='date', prediction_length=30)
```

---

### 17.3 `auto_sklearn_classify()`
**Description:** Auto-sklearn classification: Automated algorithm selection + hyperparameter tuning + ensembling.

**Example:**
```python
auto_sklearn_classify(target='category', time_left_for_this_task=300, per_run_time_limit=30)
```

---

### 17.4 `auto_sklearn_regress()`
**Description:** Auto-sklearn regression: Automated algorithm selection + hyperparameter tuning + ensembling.

**Example:**
```python
auto_sklearn_regress(target='price', time_left_for_this_task=300, per_run_time_limit=30)
```

---

### 17.5 `list_available_models()`
**Description:** List all trained AutoGluon models with their performance metrics.

**Example:**
```python
list_available_models(csv_path='housing.csv', target='price')
```

---

## 18. Data Validation (2 tools)

### 18.1 `ge_auto_profile()`
**Description:** Auto-generate Great Expectations data quality expectations: schema, nulls, ranges, distributions.

**Example:**
```python
ge_auto_profile(csv_path='sales.csv')
```

---

### 18.2 `ge_validate()`
**Description:** Validate dataset against Great Expectations suite: check nulls, types, ranges, uniqueness.

**Example:**
```python
ge_validate(csv_path='sales.csv', expectation_suite_name='sales_suite')
```

---

## 19. Experiment Tracking (4 tools)

### 19.1 `mlflow_start_run()`
**Description:** Start MLflow experiment tracking: creates run, logs params/metrics/artifacts.

**Example:**
```python
mlflow_start_run(experiment_name='housing_models', run_name='randomforest_v1')
```

---

### 19.2 `mlflow_log_metrics()`
**Description:** Log metrics, parameters, and artifacts to MLflow for experiment tracking.

**Example:**
```python
mlflow_log_metrics(metrics={'rmse':0.15,'r2':0.85}, params={'n_estimators':100}, artifacts_json='{"plot.png":"/path/plot.png"}')
```

---

### 19.3 `mlflow_end_run()`
**Description:** End MLflow run and save all tracked data.

**Example:**
```python
mlflow_end_run()
```

---

### 19.4 `export_model_card()`
**Description:** Model documentation and governance with comprehensive model cards.

**Example:**
```python
export_model_card(model_name='fraud_detector', model_type='RandomForest', target='is_fraud')
```

---

## 20. Responsible AI (2 tools)

### 20.1 `fairness_report()`
**Description:** Fairness analysis with Fairlearn: demographic parity, equalized odds, bias metrics across sensitive attributes.

**Example:**
```python
fairness_report(target='hired', sensitive_features=['gender','race'], csv_path='hiring.csv')
```

---

### 20.2 `fairness_mitigation_grid()`
**Description:** Bias mitigation strategies: reweighting, threshold optimization, postprocessing for fairness.

**Example:**
```python
fairness_mitigation_grid(target='loan_approved', sensitive_features=['race'], constraints=['demographic_parity'])
```

---

## 21. Drift Detection (2 tools)

### 21.1 `drift_profile()`
**Description:** Data/model drift detection with Evidently: distribution shifts, feature drift, target drift.

**Example:**
```python
drift_profile(reference_csv='train_data.csv', current_csv='prod_data.csv')
```

---

### 21.2 `data_quality_report()`
**Description:** Comprehensive data quality report: missing values, duplicates, correlations, drift.

**Example:**
```python
data_quality_report(csv_path='sales.csv')
```

---

## 22. Causal Inference (2 tools)

### 22.1 `causal_identify()`
**Description:** Identify causal relationships using DoWhy: backdoor, frontdoor, instrumental variables.

**Example:**
```python
causal_identify(treatment='marketing_spend', outcome='sales', csv_path='campaign.csv')
```

---

### 22.2 `causal_estimate()`
**Description:** Estimate causal effects: ATE, CATE, using regression, matching, propensity scores.

**Example:**
```python
causal_estimate(treatment='price_discount', outcome='conversion', method='backdoor', csv_path='sales.csv')
```

---

## 23. Feature Engineering (Advanced) (2 tools)

### 23.1 `auto_feature_synthesis()`
**Description:** Automated feature generation with Featuretools: creates polynomial, interaction, aggregation features.

**Example:**
```python
auto_feature_synthesis(entity_col='customer_id', time_col='date', csv_path='transactions.csv')
```

---

### 23.2 `feature_importance_stability()`
**Description:** Feature importance stability analysis: measures consistency across folds/samples.

**Example:**
```python
feature_importance_stability(target='churn', n_runs=10, csv_path='customers.csv')
```

---

## 24. Imbalanced Learning (2 tools)

### 24.1 `rebalance_fit()`
**Description:** Handle imbalanced data: SMOTE, ADASYN, random over/undersampling for better class balance.

**Example:**
```python
rebalance_fit(target='fraud', strategy='smote', csv_path='transactions.csv')
```

---

### 24.2 `calibrate_probabilities()`
**Description:** Calibrate prediction probabilities: isotonic regression, Platt scaling for better confidence.

**Example:**
```python
calibrate_probabilities(target='churn', method='isotonic', csv_path='customers.csv')
```

---

## 25. Time Series (2 tools)

### 25.1 `ts_prophet_forecast()`
**Description:** Facebook Prophet forecasting: handles seasonality, holidays, missing data, trend changes.

**Example:**
```python
ts_prophet_forecast(target='sales', datetime_col='date', periods=90, csv_path='daily_sales.csv')
```

---

### 25.2 `ts_backtest()`
**Description:** Time series backtesting: walk-forward validation, rolling window evaluation.

**Example:**
```python
ts_backtest(target='sales', datetime_col='date', test_periods=30, csv_path='daily_sales.csv')
```

---

## 26. Embeddings & Search (2 tools)

### 26.1 `embed_text_column()`
**Description:** Generate sentence embeddings using transformers: converts text to dense vectors for similarity.

**Example:**
```python
embed_text_column(text_col='description', model='all-MiniLM-L6-v2', csv_path='products.csv')
```

---

### 26.2 `vector_search()`
**Description:** Semantic similarity search using FAISS: find similar items by meaning, not keywords.

**Example:**
```python
vector_search(query='laptop computer', text_col='description', k=10, csv_path='products.csv')
```

---

## 27. Data Versioning (2 tools)

### 27.1 `dvc_init_local()`
**Description:** Initialize DVC (Data Version Control): track dataset versions like Git.

**Example:**
```python
dvc_init_local(storage_dir='.dvc/cache')
```

---

### 27.2 `dvc_track()`
**Description:** Track files with DVC: version control for datasets, models, pipelines.

**Example:**
```python
dvc_track(file_path='data/sales.csv', remote='local')
```

---

## 28. Monitoring (2 tools)

### 28.1 `monitor_drift_fit()`
**Description:** Fit drift detector for production monitoring: learns baseline distribution.

**Example:**
```python
monitor_drift_fit(reference_csv='train.csv', detector='ks')
```

---

### 28.2 `monitor_drift_score()`
**Description:** Score new data for drift: detects if production data shifted from training data.

**Example:**
```python
monitor_drift_score(new_csv='prod_batch.csv', detector='ks')
```

---

## 29. Fast Query & EDA (2 tools)

### 29.1 `duckdb_query()`
**Description:** Fast SQL queries with DuckDB: blazing fast analytics, 100x faster than pandas.

**Example:**
```python
duckdb_query(sql='SELECT category, AVG(price) FROM data GROUP BY category', csv_path='sales.csv')
```

---

### 29.2 `polars_profile()`
**Description:** Ultra-fast profiling with Polars: lightning-fast statistics, 10x faster than pandas.

**Example:**
```python
polars_profile(csv_path='large_data.csv')
```

---

## 30. Deep Learning (3 tools)

### 30.1 `train_dl_classifier()`
**Description:** Deep Learning classifier: PyTorch + Lightning + AMP + early stopping + GPU support. For large datasets (>100K rows) or high-dimensional data (>50 features).

**Example:**
```python
train_dl_classifier(data_path='large_data.csv', target='category', features=['f1','f2','f3'], params_json='{"epochs":20,"batch_size":128}')
```

---

### 30.2 `train_dl_regressor()`
**Description:** Deep Learning regressor: PyTorch + Lightning + AMP + early stopping + GPU support. For large datasets (>100K rows) or high-dimensional data (>50 features).

**Example:**
```python
train_dl_regressor(data_path='large_data.csv', target='price', features=['f1','f2','f3'], params_json='{"epochs":15,"learning_rate":0.001}')
```

---

### 30.3 `check_dl_dependencies()`
**Description:** Check if deep learning dependencies (PyTorch, Lightning, etc.) are installed and GPU is available.

**Example:**
```python
check_dl_dependencies()
```

---

## 📊 Tool Usage Statistics

**Total Tools:** 150+

**Categories:** 30

**Most Common Tasks:**
1. Data Cleaning & Preprocessing (14 tools)
2. Statistical Inference & ANOVA (34 tools)
3. Advanced Modeling (22 tools)
4. Model Training & Prediction (16 tools)

**Quick Access:**
- Type `help()` to see all tools with examples
- Type `present_full_tool_menu()` for LLM-generated stage-aware recommendations
- Type `sklearn_capabilities()` to list all sklearn algorithms

---

## 🔍 Finding the Right Tool

### By Task:
- **Data Cleaning:** `robust_auto_clean_file()`, `detect_metadata_rows()`, `impute_knn()`
- **Quick Analysis:** `describe()`, `analyze_dataset()`, `plot()`
- **Model Training:** `autogluon_automl()`, `train_classifier()`, `recommend_model()`
- **Model Evaluation:** `evaluate()`, `accuracy()`, `explain_model()`
- **Reporting:** `export_executive_report()`, `export()`, `export_model_card()`
- **Statistical Testing:** `stats()`, `anova()`, `inference()`, + 34 specialized tests
- **Time Series:** `ts_prophet_forecast()`, `smart_autogluon_timeseries()`, `arima_forecast_tool()`
- **Text Processing:** `extract_text()`, `chunk_text()`, `embed_and_index()`, `semantic_search()`
- **Unstructured Data:** 7 specialized tools for PDFs, images, audio, emails

### By Workflow Stage:
1. **Data Collection:** `discover_datasets()`, `list_data_files()`
2. **Cleaning:** `robust_auto_clean_file()`, `detect_metadata_rows()`
3. **EDA:** `describe()`, `analyze_dataset()`, `stats()`
4. **Visualization:** `plot()`, `correlation_plot()`, `pairplot()`
5. **Feature Engineering:** `auto_feature_synthesis()`, `expand_features()`, `select_features()`
6. **Statistical Analysis:** `stats()`, `anova()`, `inference()` + 34 tests
7. **Model Training:** `autogluon_automl()`, `train_classifier()`, `train_regressor()`
8. **Model Evaluation:** `evaluate()`, `accuracy()`, `explain_model()`
9. **Prediction:** `predict()`, `classify()`, `ensemble()`
10. **Deployment:** `export_onnx_tool()`, `monitor_drift_fit()`
11. **Reporting:** `export_executive_report()`, `export()`
12. **Specialized:** Causal inference, fairness, drift detection, deep learning

---

## 💡 Tips

1. **Start Simple:** Use `describe()` or `analyze_dataset()` for quick insights
2. **Auto-Clean:** `robust_auto_clean_file()` handles most data quality issues
3. **Let AI Help:** `recommend_model()` suggests the best algorithms for your data
4. **AutoML First:** Try `smart_autogluon_automl()` for quick baseline models
5. **Explain Results:** Always use `explain_model()` to understand predictions
6. **Document Everything:** Use `export_executive_report()` for comprehensive documentation
7. **Test Thoroughly:** Use 34 statistical tests for rigorous analysis
8. **Process Unstructured Data:** 7 tools for PDFs, images, audio, emails

---

**Last Updated:** October 24, 2025  
**Total Tools:** 150+  
**Documentation Version:** 1.0

