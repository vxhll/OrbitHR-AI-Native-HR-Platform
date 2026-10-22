\# OrbitHR — Operational Data Compatibility Assessment



\## 1. Purpose



This document records the compatibility gap between OrbitHR's operational PostgreSQL database and the synthetic event-based attrition model (`event-based-v3`).



The objective is to prevent incompatible data from being passed into a model that has not been trained or validated for those operational records.



\## 2. Current Architecture



OrbitHR currently has two separate attrition prediction paths.



\### Baseline prediction path



\- \*\*Endpoint:\*\* `GET /api/analytics/attrition-predict/{employee\_id}`

\- \*\*Model version:\*\* `baseline-1.0`

\- \*\*Purpose:\*\* Preserve the existing baseline prediction functionality.

\- \*\*Status:\*\* Existing endpoint verified successfully.



\### Event-based prediction path



\- \*\*Endpoint:\*\* `GET /api/analytics/attrition-predict-v3/{employee\_id}?prediction\_date=YYYY-MM-DD`

\- \*\*Model version:\*\* `event-based-v3`

\- \*\*Feature service:\*\* `ml/attrition/event\_based\_feature\_service.py`

\- \*\*Prediction service:\*\* `ml/attrition/event\_based\_prediction\_service.py`

\- \*\*Model artifact:\*\* `ml/attrition/attrition\_event\_based\_logistic\_regression.joblib`

\- \*\*Data source:\*\* `data/synthetic\_v3/`

\- \*\*Status:\*\* Functional research prototype using synthetic data.



The v3 prediction service currently reads the synthetic employee and HR-event files. It does not construct predictions from the operational PostgreSQL employee, attendance, performance, engagement, leave, and payroll tables.



\## 3. Operational Data Inventory



The following inventory was observed during development.



| Operational dataset | Observed coverage or volume | Temporal representation               |

| ------------------- | --------------------------- | ------------------------------------- |

| Attendance          | 60,848 records              | Daily dates, January–June 2026        |

| Performance reviews | 905 records                 | Quarterly periods, 2026-Q1 to 2026-Q2 |

| Engagement surveys  | 2,106 records               | Monthly periods, January–June 2026    |

| Leave records       | 1,554 records               | Start dates, January–June 2026        |

| Payroll             | 2,863 records               | Payment dates, January–June 2026      |



These are development-time observations, not a guarantee that record counts or date ranges remain unchanged.



\## 4. Synthetic Model Data Design



The event-based model was trained and evaluated using synthetic data containing:



\- 1,200 synthetic employees.

\- Approximately 975,400 synthetic HR events.

\- 12,249 temporal employee snapshots.

\- A 90-day historical feature window.

\- A synthetic attrition target over the following 180 days.

\- Snapshot dates from January through December 2025.



The model uses 17 source features, with department one-hot encoding producing 22 transformed features.



The saved model's holdout metrics describe the synthetic evaluation dataset only.



\## 5. Identified Compatibility Gaps



\### 5.1 Temporal granularity



The synthetic dataset uses dated events to construct features for a defined 90-day lookback window.



Operational attendance records have daily dates, but performance reviews use quarterly period labels and engagement surveys use monthly period labels. These records do not provide the same event-level temporal resolution.



A compatibility pipeline must define which observations belong to each prediction window and how to handle period-based records without inventing unsupported event dates.



\### 5.2 Prediction-date coverage



The synthetic v3 snapshots cover January–December 2025, with a future 180-day label window supported by the simulation's event history.



The operational records observed during development cover January–June 2026 for the listed datasets.



The synthetic prediction dates and operational data periods are different. A production-oriented model requires appropriately dated historical features and a valid outcome window for its training and evaluation data.



\### 5.3 Department categories



The synthetic dataset includes:



\- Engineering

\- Sales

\- Human Resources

\- Finance

\- Operations

\- Customer Support



The operational database contains additional department categories, including IT, Legal, Marketing, and Product, and uses different department naming conventions.



The trained one-hot encoder was not validated for the operational department vocabulary. Unknown categories must be handled deliberately, and the model must be evaluated on compatible data before operational use.



\### 5.4 Job-level representation



Synthetic records represent `job\_level` as an integer from 1 to 5.



Operational employee records use string labels such as `L2 - Executive`.



A mapping cannot safely be assumed from the labels alone. Any mapping must be explicitly defined, checked against the organization's job-level structure, and applied consistently during training and inference.



\### 5.5 Feature semantics and missing values



The model expects 17 specific features with defined meanings and a 90-day observation window.



Operational database columns must not be mapped to those features merely because their names appear similar. Each feature requires a documented source, aggregation rule, unit, observation window, and missing-data policy.



For example, the synthetic attendance features count attendance events and absence values according to the synthetic generator's conventions. Operational attendance status values must be interpreted explicitly before equivalent features can be constructed.



\## 6. Required Compatibility Work



Before using operational data for v3 predictions, complete the following work.



1\. \*\*Define the feature contract.\*\* Document each model feature's source table, source columns, time window, aggregation, units, and missing-value behavior.

2\. \*\*Implement a separate operational feature pipeline.\*\* Build features as of a specified prediction date, using only information available before that date.

3\. \*\*Resolve temporal aggregation.\*\* Define defensible rules for quarterly performance reviews, monthly engagement surveys, daily attendance, leave, and payroll.

4\. \*\*Normalize categorical values.\*\* Establish and validate the department vocabulary and an explicit job-level mapping.

5\. \*\*Validate feature parity.\*\* Test feature construction against independently calculated examples and enforce the exact model input schema.

6\. \*\*Obtain suitable training labels.\*\* Define real historical attrition outcomes and a reliable 180-day outcome window if retaining the current target horizon.

7\. \*\*Train and evaluate appropriately.\*\* Use operationally compatible data and employee-disjoint, time-aware evaluation. Compare against appropriate baselines and examine precision, recall, calibration, and subgroup performance.

8\. \*\*Add API safeguards.\*\* Reject unsupported dates, missing required data, and incompatible feature inputs with clear errors.

9\. \*\*Keep model versions separate.\*\* Do not replace the existing baseline model until the alternative has passed documented validation and regression testing.

10\. \*\*Review responsible-use controls.\*\* Require human review and prohibit automatic punitive employment decisions based solely on a risk score.



\## 7. Current Safety Boundary



The v3 endpoint is a research prototype that uses synthetic data. Its predictions must not be represented as validated risk estimates for real employees.



Until operational compatibility and validation are complete:



\- Do not pass operational employee IDs into the v3 endpoint expecting PostgreSQL-backed predictions.

\- Do not claim that the v3 model is integrated with the operational HR database.

\- Do not interpret synthetic holdout metrics as evidence of real-world accuracy.

\- Do not use synthetic model scores to make employment decisions.

\- Preserve the existing baseline endpoint and its separate model version.



\## 8. Verification Checklist



\- \[x] Event-based feature service implemented.

\- \[x] Event-based prediction service implemented.

\- \[x] Synthetic snapshot feature parity validated for the tested example.

\- \[x] Prediction explanation reconstruction covered by an automated test.

\- \[x] Automated test suite passed at the current development checkpoint.

\- \[x] Baseline API returned HTTP 200 with `baseline-1.0`.

\- \[x] V3 API returned HTTP 200 with `event-based-v3` and 22 explanation contributions.

\- \[x] Model card documented.

\- \[ ] Operational feature contract defined.

\- \[ ] Operational feature pipeline implemented and validated.

\- \[ ] Real historical attrition labels and suitable evaluation data established.

\- \[ ] Operational model evaluation and responsible-use review completed.



\## 9. Conclusion



OrbitHR has a working synthetic event-based attrition research prototype with automated tests and additive model explanations. The existing baseline API remains functional.



The next major integration task is to establish a validated bridge between operational HR data and the model's feature contract. That work requires explicit temporal aggregation, categorical compatibility, reliable outcome labels, and independent evaluation; it must not be treated as a simple database-column mapping exercise.
