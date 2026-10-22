\# OrbitHR — Temporal Attrition Dataset Design



\## 1. Objective

Build a reproducible synthetic dataset to evaluate whether employee information available at a prediction date can help predict attrition during the following 180 days.



\## 2. Prediction Snapshots

\- Frequency: Monthly

\- Prediction dates: January 1, 2025 through December 1, 2025

\- Each employee may contribute multiple snapshots.

\- An employee must have been hired before the prediction date.



\## 3. Feature Window

Use records from the 90 days immediately preceding each prediction date. Features must only use information available on or before that date.



Candidate features include:

\- Employee age, tenure, job level, department and base salary

\- Attendance and absence patterns

\- Recent performance and manager feedback

\- Engagement, job satisfaction and employee NPS

\- Leave patterns and payroll history

\- Changes in relevant measures over time, where sufficient history exists



Do not use future records, exit dates, exit reasons, current employment status, or target labels as predictors.



\## 4. Target Definition

`attrited\_within\_180\_days\_label`:

\- `1`: The employee exits after the prediction date and within the next 180 calendar days, inclusive.

\- `0`: The employee remains employed throughout the complete 180-day outcome window.

\- Exclude snapshots without a complete outcome window or with insufficiently known employment outcomes.



\## 5. Synthetic Data Requirements

\- Preserve all existing synthetic CSV files as the baseline.

\- Generate a separate versioned dataset with documented generation rules and random seed.

\- Include historical feature records and exit events spanning all required windows.

\- Generate realistic relationships between selected risk signals and future exits without making the target directly recoverable from a single feature.

\- Clearly identify all data as synthetic.



\## 6. Leakage Prevention

\- Features must be calculated independently for each employee and prediction date.

\- Exclude all information occurring after the prediction date.

\- Split training and test data by employee so the same employee does not appear in both sets.

\- Fit preprocessing and feature transformations on training data only.



\## 7. Evaluation

Report:

\- Positive and negative label counts

\- Precision, recall, F1-score and ROC-AUC

\- Confusion matrix

\- Baseline comparison

\- Validation limitations and synthetic-data caveats



Do not treat synthetic test performance as evidence of real-world predictive accuracy.



\## 8. Responsible Use

Predictions are decision-support signals for authorized HR reviewers. Risk scores must not automatically trigger termination, disciplinary action, or other punitive employment decisions.
