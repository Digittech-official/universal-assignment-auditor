# Severity Scale

| Severity | Meaning | Allowed basis |
|---|---|---|
| CRITICAL | A mandatory requirement is missing/failed in a way that would likely cause failure of the task or of a criterion, or a fundamental integrity problem (wrong task answered, core deliverable absent, code that cannot meet the core specification). | MANDATORY_REQUIREMENT or RUBRIC_CRITERION only |
| MAJOR | A mandatory requirement or rubric criterion is substantially weak or partially met; significant effect on quality/mark. | MANDATORY_REQUIREMENT, RUBRIC_CRITERION, or BEST_PRACTICE when it materially affects correctness (e.g. a wrong statistical test, a security flaw) |
| MODERATE | Clear improvement that would raise quality; not decisive. | Any |
| MINOR | Polish: wording, formatting consistency, small clarity issues. | Any |

- Every CRITICAL and MAJOR finding is independently verified by Agent 12 before release.
- Best practice is **never** CRITICAL. Optional / recommended requirements never ground CRITICAL or MAJOR.
- Priority in the revision plan follows severity, then effort (quick wins first within a severity).
