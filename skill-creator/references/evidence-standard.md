# Skill execution evidence standard

Every skill must have evidence from an actual execution. Documentation, a successful lint,
a generated mockup, or a screenshot of an editor is not execution evidence.

## Evidence levels

| Level | Meaning | Permitted claim |
|---|---|---|
| DRAFT | Instructions exist; no executable check was run | Designed, not tested |
| STATIC_CHECKED | Structure/frontmatter/references passed lint | Static checks passed |
| SCRIPT_TESTED | Bundled scripts or self-tests ran and passed | Named script tests passed |
| HOST_EXECUTED | A real supported agent host discovered and activated the skill | Skill activated in the named host |
| BEHAVIOR_VERIFIED | A real host executed defined scenarios and met assertions | Only named scenarios are verified |

Never promote a skill to a higher level based on lower-level evidence.

## Required evidence

- Exact skill and scenario name.
- Exact command or host action.
- Run timestamp, runtime/platform, and tool/model identity when available.
- Exit status and unedited stdout/stderr or host trace.
- Screenshot captured by the test runner from the actual run/report.
- Assertions and pass/fail result.
- Known limitations and skipped checks.

Never invent model IDs, session IDs, tool calls, timestamps, logs, screenshots, or results.
If the host does not expose a value, record "not exposed"; do not infer it.

## Capture and storage

The repository workflow runs each skill's scripts/selftest.py, creates JSON/Markdown/HTML
reports, captures the report with Playwright, and uploads evidence as a GitHub Actions artifact.
Raw stdout/stderr are retained per skill.

Artifacts belong to the exact workflow run and commit. Open the Actions run and download its
skill-execution-evidence artifact. Never label an old screenshot as current evidence.

## Scope boundary

The repository-wide runner proves only that bundled self-test scripts executed. It does not
prove LLM-host discovery, activation, or instruction-following. Those require host-specific
integration scenarios that invoke the actual skill in the target runtime and capture its real UI/trace.

If a skill has no scripts/selftest.py, report NOT_TESTED. Missing tests are not a pass.
If an optional dependency is unavailable, report the affected test as skipped or unverified.

## Release rule

Claim SCRIPT_TESTED only when the latest run artifact shows a passing self-test.
Claim HOST_EXECUTED or BEHAVIOR_VERIFIED only with corresponding host-run evidence.
A screenshot without its run log and assertions is insufficient.
