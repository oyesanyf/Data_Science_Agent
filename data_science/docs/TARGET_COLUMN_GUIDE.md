# Target Column Selection Guide

## Quick Answer

**Yes, you need to specify ONE target column for each model training run.**

- **Target column** = What you want to predict
- **Feature columns** = All other columns used to make predictions
- **You can train multiple models for different targets** - just run them separately

---

## Understanding Target vs Features

### What is a Target Column?

The **target column** (also called "label" or "dependent variable") is:
- The column you want to predict
- The outcome you're trying to model
- What the machine learning model will learn to forecast

### What are Feature Columns?

**Feature columns** (also called "predictors" or "independent variables") are:
- All other columns in your dataset
- Used as inputs to predict the target
- The "evidence" the model uses to make predictions

---

## Example: Election Data

### Your Dataset
```
candidate | party      | state | candidatevotes | totalvotes
---------|------------|-------|----------------|------------
Biden    | Democrat   | CA    | 11110000       | 17500000
Trump    | Republican | CA    | 6006000        | 17500000
Biden    | Democrat   | TX    | 5259000        | 11300000
...
```

### Option 1: Predict Candidate Votes
```python
# Target: candidatevotes (what we want to predict)
# Features: party, state, totalvotes (used to predict)

smart_autogluon_automl(
    target='candidatevotes',
    csv_path='election_data.csv'
)
```

**This model predicts:** How many votes a candidate will get based on their party, state, and total votes.

### Option 2: Predict Total Votes
```python
# Target: totalvotes (what we want to predict)
# Features: party, state, candidatevotes (used to predict)

smart_autogluon_automl(
    target='totalvotes',
    csv_path='election_data.csv'
)
```

**This model predicts:** How many total votes will be cast based on party, state, and candidate votes.

### Option 3: Predict Party
```python
# Target: party (what we want to predict)
# Features: state, candidatevotes, totalvotes (used to predict)

smart_autogluon_automl(
    target='party',
    csv_path='election_data.csv'
)
```

**This model predicts:** Which party a candidate belongs to based on their vote patterns.

---

## Can I Use Multiple Targets?

**Yes, but ONE at a time!**

### Approach 1: Train Sequentially
```python
# Train model 1
smart_autogluon_automl(target='candidatevotes', csv_path='election_data.csv')

# Train model 2
smart_autogluon_automl(target='totalvotes', csv_path='election_data.csv')

# Train model 3
smart_autogluon_automl(target='party', csv_path='election_data.csv')
```

### Approach 2: Compare Results
```python
# Option A: Predict candidate votes
accuracy(target='candidatevotes', csv_path='election_data.csv')

# Option B: Predict party affiliation
accuracy(target='party', csv_path='election_data.csv')

# Compare which target is more predictable!
```

---

## Choosing the Right Target

### Ask Yourself:

1. **What do I want to predict?**
   - Future sales? → Target: `sales`
   - Customer churn? → Target: `churned`
   - House prices? → Target: `price`

2. **What type of prediction?**
   - **Regression** (numeric): Predict amounts, prices, quantities
   - **Classification** (categories): Predict yes/no, types, classes

3. **Do I have enough data?**
   - Target should have enough variation
   - Avoid targets with 99% the same value

### Common Target Examples

| Use Case | Dataset | Target Column | Type |
|----------|---------|---------------|------|
| Sales forecasting | Sales data | `revenue` | Regression |
| Customer churn | User activity | `will_churn` | Classification |
| House pricing | Real estate | `sale_price` | Regression |
| Spam detection | Emails | `is_spam` | Classification |
| Stock prediction | Financial | `next_day_price` | Regression |
| Disease diagnosis | Medical | `has_disease` | Classification |
| Election outcomes | Voting | `candidatevotes` | Regression |

---

## How to Let the Agent Help

### Option 1: Explore First
```
"Can you analyze my data and suggest which columns would make good targets?"
```

The agent will:
- Run `analyze_dataset()`
- Show column types and distributions
- Suggest potential targets

### Option 2: Ask for Recommendations
```
"I have election data with columns: candidate, party, state, candidatevotes, totalvotes.
What should I predict?"
```

The agent will:
- Explain each column
- Suggest which targets make sense
- Recommend the best approach

### Option 3: Try Multiple Targets
```
"Train models for candidatevotes, then for party, then compare which works better"
```

The agent will:
- Train model for `candidatevotes`
- Train model for `party`
- Compare accuracy metrics
- Tell you which target is more predictable

---

## Common Questions

### Q: Can I predict multiple columns at once?
**A:** Not directly. Train separate models for each target you want to predict.

### Q: What if I don't know which target to use?
**A:** Ask the agent to `analyze_dataset()` - it will suggest good targets based on your data.

### Q: Can features include the target?
**A:** No! The model automatically excludes the target column from features. You can't use `candidatevotes` to predict `candidatevotes`.

### Q: What if my target has missing values?
**A:** The agent will drop rows with missing target values automatically. Features can have missing values (they'll be imputed).

### Q: Can I use ALL columns as features?
**A:** Yes (except the target)! The agent uses all other columns as features by default. You can use feature selection tools to reduce them.

---

## Practical Workflows

### Workflow 1: Exploratory Analysis
```
1. Upload your CSV
2. "Analyze this dataset and suggest targets"
3. Agent runs analyze_dataset()
4. Agent suggests: "You could predict: candidatevotes (regression) or party (classification)"
5. Pick one and proceed
```

### Workflow 2: Direct Training
```
1. Upload your CSV
2. "Train a model to predict candidatevotes"
3. Agent runs smart_autogluon_automl(target='candidatevotes')
4. Done!
```

### Workflow 3: Comparison
```
1. Upload your CSV
2. "Compare: predict candidatevotes vs predict party"
3. Agent trains both models
4. Agent compares accuracy metrics
5. Agent recommends the better approach
```

---

## Example Agent Interaction

### ❌ Before (Confusing)
```
User: "Train a model on my election data"
Agent: "I need a target column. Please specify."
User: "What's a target column?" 😕
```

### ✅ After (Clear)
```
User: "Train a model on my election data"
Agent: "I need to know which column you want to predict (target). 
       Your columns: candidate, party, state, candidatevotes, totalvotes
       
       Common choices:
       - candidatevotes (predict vote counts) → Regression
       - party (predict party affiliation) → Classification
       
       Which would you like to predict?"
User: "Predict candidatevotes"
Agent: "Perfect! Training regression model for candidatevotes..." ✅
```

---

## Key Takeaways

1. ✅ **ONE target per training run** - it's the column you want to predict
2. ✅ **All other columns are features** - used to make predictions
3. ✅ **You CAN train multiple models** - just run them separately
4. ✅ **Target type determines task** - numeric=regression, categorical=classification
5. ✅ **Agent can help you choose** - use `analyze_dataset()` for suggestions
6. ✅ **Don't overthink it** - start with the most interesting column to predict!

---

## Agent Updated Behavior

The agent now:
- ✅ Explains target vs features clearly
- ✅ Shows examples when asking for target
- ✅ Suggests good targets based on column types
- ✅ Offers to train multiple models for comparison
- ✅ Recommends using `analyze_dataset()` when user is unsure

---

## Quick Reference

```python
# Basic pattern for ANY model training
model_function(
    target='column_to_predict',      # ONE column
    csv_path='your_data.csv'
)

# Examples with different tools
smart_autogluon_automl(target='candidatevotes', csv_path='data.csv')
auto_sklearn_classify(target='party', csv_path='data.csv')
train_classifier(target='spam', csv_path='emails.csv')
accuracy(target='price', csv_path='houses.csv')
ensemble(target='churn', csv_path='customers.csv')
```

---

## Need Help?

Try these commands in the agent:
```
- "help()" - See all 41 tools
- "analyze_dataset()" - Explore your data and get target suggestions
- "What should I predict in this dataset?" - Get AI recommendations
- "Explain target vs features with examples" - More detailed explanation
```

---

## Summary

🎯 **Target** = What you predict (ONE column)  
📊 **Features** = What you use to predict (all other columns)  
🚀 **Multiple targets?** = Train multiple models separately  
💡 **Not sure?** = Ask the agent to analyze your data first!

The agent is now smarter about explaining this and will guide you through the process! 🎉

