# Notes for certification — {{APP_NAME}} {{VERSION}}

Text für das Feld „Notes for certification" im Partner Center (Englisch). Ziel: Der Microsoft-Validator kann die App ohne Rückfrage installieren, einrichten und die Kernpfade testen.

## Installation and setup

1. Install the app from the submission package in a Business Central sandbox (version ≥ _…_).
2. Open **Assisted Setup** → **{{APP_NAME}}** and complete the wizard. Required values: _…_
3. Assign permission set **_…_** to the test user.

## Licensing during validation

- Users without a purchased plan run in read-only mode by design. To test write scenarios, _describe how the validator gets a licensed state (e.g. publisher/internal entitlement, trial, or a test plan)_.

## External services

- The app calls _service_ at _endpoint_. For validation, _describe how to test without a paid key (mock mode, demo key, or a documented error path)_.
- No data is sent to third parties unless the administrator enters credentials in **_setup page_**.

## Test scenarios

| # | Scenario | Steps | Expected result |
|---|----------|-------|-----------------|
| 1 | _Happy path_ | _…_ | _…_ |
| 2 | _Read-only user_ | _…_ | _actions disabled, tooltip names required plan_ |
| 3 | _Error path (external service unavailable)_ | _…_ | _friendly error, no data loss_ |

## Contacts

- Engineering contact: _name, e-mail, phone (digits and spaces only)_
- Response time for validator questions: within 1 business day.
