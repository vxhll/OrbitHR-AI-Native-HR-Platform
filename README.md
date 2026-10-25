# OrbitHR — AI-Native HR Platform

OrbitHR is an AI-native Human Resources platform built to support HR operations, workforce analytics, and onboarding automation.

## Onboarding Reminder Automation

### Overview

The onboarding reminder workflow connects the OrbitHR FastAPI backend with Microsoft Power Automate Desktop (PAD). It retrieves overdue onboarding tasks, evaluates the API response, and conditionally initiates reminder processing.

### Architecture

```text
PostgreSQL Database
        |
        v
OrbitHR FastAPI Backend
        |
        v
Power Automate Desktop
        |
        v
Retrieve Overdue Tasks
        |
        v
Parse JSON Response
        |
        v
Check total_overdue_tasks > 0
        |
        +---- Yes ----> Run Reminder API (dry-run)
        |
        +---- No -----> Skip Reminder API
```

### Configured Workflow

Flow name: `OrbitHR_Onboarding_Reminder_Test`

1. Check backend connectivity using `GET /docs`.
2. Retrieve overdue tasks using `GET /api/onboarding/automation/overdue-tasks`.
3. Convert the JSON response into a custom object.
4. Evaluate whether `total_overdue_tasks > 0`.
5. If overdue tasks exist, call `POST /api/onboarding/automation/reminders/run?dry_run=true`.
6. Skip reminder processing when no overdue tasks are reported.

### Validation Results

- Backend connectivity request returned HTTP 200.
- Overdue-tasks API returned HTTP 200.
- JSON conversion succeeded.
- The observed overdue-task count was zero.
- The reminder endpoint was separately tested through Swagger with `dry_run=true`.
- That test reported `delivery_enabled=false`, `eligible_tasks=0`, and `results_count=0`.

The PAD conditional branch was configured, but its skipped-action status has not been independently confirmed in execution history.

### Security and Safety

- Keep actual email delivery disabled during development and validation.
- Keep reminder processing in dry-run mode until delivery configuration has been verified.
- Never commit Bearer tokens, database passwords, or other secrets.
- Use authorized accounts and appropriate API permissions.

### Remaining Work

- Verify the PAD conditional branch using execution details.
- Test the reminder-processing branch with a safe test scenario.
- Configure and verify scheduled execution if required.
- Complete final backend, database, and frontend integration checks.
- Update this documentation as additional functionality is verified.

### Current Limitations

Live email delivery and scheduled execution have not yet been demonstrated. The current PAD flow is a local desktop workflow and depends on its configured execution environment.
