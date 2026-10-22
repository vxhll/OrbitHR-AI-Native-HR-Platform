\# OrbitHR — Event-Based Attrition Model Card



\## 1. Model Overview



\- \*\*Project:\*\* OrbitHR — AI-Native HR Lifecycle \& Predictive Retention Platform

\- \*\*Model name:\*\* Event-Based Attrition Logistic Regression

\- \*\*Model version:\*\* `event-based-v3`

\- \*\*Algorithm:\*\* Balanced Logistic Regression

\- \*\*Artifact:\*\* `ml/attrition/attrition\_event\_based\_logistic\_regression.joblib`

\- \*\*Training data:\*\* Synthetic event-based HR dataset (`data/synthetic\_v3/`)

\- \*\*Intended use:\*\* Research and prototyping of explainable attrition-risk estimates.

\- \*\*Production status:\*\* Not production-validated.



This model estimates the probability associated with the synthetic attrition target defined by the dataset. It must not be represented as a validated prediction of real-world employee attrition.



\## 2. Prediction Design



The model uses historical features calculated from a 90-day lookback window ending immediately before each prediction date.



\- \*\*Lookback window:\*\* 90 days

\- \*\*Target horizon:\*\* 180 days after the prediction date

\- \*\*Snapshot period:\*\* January–December 2025

\- \*\*Employee records:\*\* 1,200

\- \*\*Historical HR events:\*\* Approximately 975,400

\- \*\*Temporal snapshots:\*\* 12,249

\- \*\*Raw model features:\*\* 17

\- \*\*Transformed model features:\*\* 22, including encoded department categories



The dataset generator and validator are preserved as separate artifacts. The event-based dataset validator previously passed 22 validation checks.



\## 3. Input Features



\### Employee and employment features



\- `age`

\- `tenure\_years`

\- `job\_level`

\- `annual\_base\_salary\_inr`

\- `department`



\### Attendance features



\- `attendance\_record\_count\_90d`

\- `average\_hours\_worked\_90d`

\- `absent\_days\_90d`



\### Performance and career features



\- `average\_performance\_rating\_90d`

\- `average\_manager\_feedback\_score\_90d`

\- `promotion\_count\_90d`



\### Engagement features



\- `average\_engagement\_score\_90d`

\- `average\_job\_satisfaction\_score\_90d`

\- `average\_employee\_nps\_90d`



\### Leave and payroll features



\- `leave\_record\_count\_90d`

\- `total\_leave\_days\_90d`

\- `payroll\_record\_count\_90d`



Numeric features use median imputation and scaling. The categorical department feature uses most-frequent imputation and one-hot encoding.



\## 4. Evaluation Results



The following metrics are from the saved `event-based-v3` model's employee-disjoint temporal holdout evaluation.



| Metric | Test result |

|---|---:|

| Accuracy | 0.8026 |

| Precision | 0.1842 |

| Recall | 0.4828 |

| F1 score | 0.2667 |

| ROC-AUC | 0.7290 |

| Average precision | 0.2227 |



The majority-class baseline achieved 0.9256 accuracy and an F1 score of 0. These results demonstrate why accuracy alone is insufficient for evaluating an imbalanced attrition dataset.



\### Interpretation



\- The model identifies some positive attrition cases, but precision is low.

\- False-positive predictions are a material limitation.

\- ROC-AUC indicates some ability to distinguish the synthetic classes, not proven real-world predictive performance.

\- These metrics describe the synthetic holdout only.

\- The results do not establish business impact, fairness, calibration, or production readiness.



\## 5. Prediction Thresholds and Risk Bands



The saved model's binary classification threshold is approximately `0.55`.



The API separately displays these risk bands:



\- \*\*High:\*\* Probability greater than or equal to 70%.

\- \*\*Medium:\*\* Probability greater than or equal to 40% and below 70%.

\- \*\*Low:\*\* Probability below 40%.



The risk-band thresholds are presentation categories. They are not the same as the binary classification threshold.



Thresholds require further evaluation before operational use. In particular, the cost of false positives and false negatives should be considered before setting intervention policies.



\## 6. Explainability



The API returns a logistic-regression contribution decomposition.



For each transformed feature, its contribution is calculated from the transformed feature value multiplied by the corresponding logistic-regression coefficient. The contributions are aggregated by source feature where appropriate.



The response includes:



\- Explanation method

\- Baseline log-odds

\- Reconstructed log-odds

\- Top positive contributions

\- Top negative contributions

\- Full contribution list



The reconstructed log-odds are checked against the model's decision function by an automated test.



\### Important limitations



\- Contributions describe how model inputs combine mathematically to produce the model score.

\- Positive and negative contributions are not proof of causal relationships.

\- Contributions are expressed on the log-odds scale, not as percentage-point changes in probability.

\- One-hot-encoded department contributions are associated with the source `department` feature.

\- Explanations do not establish that an employee will leave or explain why an individual might leave.



\## 7. Data Compatibility and Operational Limitations



The v3 prediction service currently reads the synthetic v3 dataset. It is not connected to the operational PostgreSQL employee records for prediction.



The operational database differs from the synthetic training data in important ways:



\- Operational performance reviews use quarterly periods, while the synthetic feature design relies on event dates within a 90-day window.

\- Operational engagement surveys use monthly periods, while the synthetic design uses dated events.

\- Operational department names include categories not represented in the synthetic training data.

\- Operational job levels use string labels such as `L2 - Executive`, while synthetic job levels are integers from 1 to 5.

\- Operational data covers a different period from the synthetic model's training and evaluation snapshots.



Consequently, the current model must not be applied directly to operational employees by simply mapping database columns into the model.



A separate compatibility pipeline, explicit missing-data and category handling, suitable training data, and independent validation would be required before real operational use.



\## 8. Responsible Use



This model is a research prototype, not an automated employment decision system.



\- Do not use its output as the sole basis for hiring, termination, promotion, compensation, performance management, or other consequential employment decisions.

\- Do not automatically trigger punitive actions based on risk scores.

\- Require qualified human review before considering any retention intervention.

\- Evaluate fairness, privacy, data quality, calibration, and subgroup performance before any real-world deployment.

\- Treat synthetic-data metrics as experimental evidence only.



A model risk score should be used, at most, as a prompt for careful review and supportive retention analysis—not as a judgment about an employee.



\## 9. Reproducibility and Verification



Relevant artifacts:



\- `ml/attrition/generate\_event\_based\_dataset.py`

\- `ml/attrition/validate\_event\_based\_dataset.py`

\- `ml/attrition/train\_event\_based\_model.py`

\- `ml/attrition/evaluate\_event\_based\_holdout.py`

\- `ml/attrition/event\_based\_feature\_service.py`

\- `ml/attrition/event\_based\_prediction\_service.py`

\- `tests/test\_event\_based\_feature\_service.py`

\- `tests/test\_event\_based\_prediction\_service.py`

\- `ml/evaluation/event\_based\_attrition\_metrics.json`



The feature-service tests, prediction-service tests, snapshot feature-parity validation, and live API check have passed at the current development checkpoint.



The v3 API is exposed at:



`GET /api/analytics/attrition-predict-v3/{employee\_id}?prediction\_date=YYYY-MM-DD`



The original baseline endpoint remains separate:



`GET /api/analytics/attrition-predict/{employee\_id}`



\## 10. Current Status



\*\*Status:\*\* Functional research prototype with automated tests and additive model explanations.



\*\*Next steps:\*\* Complete the documentation, run the full regression suite, verify both API endpoints, and document the operational-data compatibility gap before starting dashboard integration.
