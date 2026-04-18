# AGENTS.md — no-animal-violence-action

## Summary

`no-animal-violence-action` is a composite GitHub Action that scans pull requests and repository files for speciesist language and fails CI when violations at or above a configured severity threshold are found. It embeds 65+ detection rules inline, installs the [woke](https://github.com/get-woke/woke) linter at runtime, runs a two-pass scan (display then gate), and posts inline PR annotations. It is the primary CI enforcement point in the Open Paws no-animal-violence tooling suite.

---

## Status

**Production** — actively used across Open Paws repos. Last substantive change: 2026-04-14 (severity gating fix, PR #14). Receives automated submodule-update commits from `open-paws-bot` but no active feature development is in progress as of 2026-04-18.

**Change implications:** This action is referenced as `Open-Paws/no-animal-violence-action@v1` by other repositories. Changes to the action's interface (input names, exit codes, annotation format) will break callers that pin to `@v1`. Behavior-only changes inside the run steps are lower risk but should always be tested against a real PR before merging.

---

## Key Files

| File | Role |
|------|------|
| `action.yml` | The entire action — inputs declaration, rule generation heredoc, and three bash/Python run steps (~950 lines) |
| `README.md` | User-facing documentation: quick start, inputs, configuration examples, ecosystem map |
| `AGENTS.md` | This file — architecture and contributor guidance for automated agents |
| `CLAUDE.md` | Claude Code session context: org decisions, known DRY violations, seven concerns notes |
| `.github/workflows/no-animal-violence.yml` | Self-check workflow — this repo runs itself on every PR |
| `.github/workflows/auto-merge.yml` | Bot-authored submodule update automation |
| `semgrep-no-animal-violence.yaml` | Semgrep config stub (complementary scanner) |
| `LICENSE` | MIT |

---

## Architecture

### Action type

Composite action — no Docker image, no Node.js runtime. All steps run in bash and Python 3 on `ubuntu-latest`. This keeps the action fast (no container pull) and simple (no build step).

### Execution flow

```
Step 1: Install woke
  └── curl | bash → /usr/local/bin/woke

Step 2: Generate rule file
  └── heredoc → /tmp/.woke.yaml  (65+ rules, all severities)

Step 3: Display run
  └── woke -c /tmp/.woke.yaml --disable-default-rules <paths> || true
      (exit code ignored — shows all violations in CI log)

Step 4: Threshold filter (Python 3)
  ├── Reads WOKE_SEVERITY env var (validated in bash beforehand)
  ├── Filters /tmp/.woke.yaml to rules at or above threshold
  ├── Writes /tmp/.woke-threshold.yaml
  └── Exits 99 if no rules match (nothing to gate on → pass)

Step 5: Gate run
  └── woke -c /tmp/.woke-threshold.yaml --disable-default-rules --exit-1-on-failure <paths>
      (exits non-zero if any violations found → CI fails)
```

### Severity model

Severity values are ordered: `error` (0) > `warning` (1) > `info` (2). The threshold filter keeps rules where `order[rule.severity] <= order[threshold]`. This means:
- `severity: error` → only `error` rules gate CI
- `severity: warning` → `error` and `warning` rules gate CI
- `severity: info` → all rules gate CI

### Rule categories embedded in action.yml

1. Violent animal idioms (`error`) — e.g., "kill two birds with one stone", "beat a dead horse", "like a chicken with its head cut off"
2. Animal-as-object metaphors (`warning`) — e.g., "guinea pig", "cash cow", "sacred cow", "scapegoat"
3. Industry euphemisms (`warning`) — e.g., "livestock", "poultry", "processing plant", "gestation crate", "spent hen"
4. Technical terminology (`warning/info`) — e.g., "cattle vs. pets", "canary deployment", "dogfooding", "herding cats"
5. Common idioms flagged for awareness (`info`) — e.g., "red herring", "pet project", "hold your horses"

### Integration points

- **Called by**: any GitHub Actions workflow via `uses: Open-Paws/no-animal-violence-action@v1`
- **Related CI**: `reviewdog-no-animal-violence` (alternative action with reviewdog output formatting)
- **Related local tooling**: `no-animal-violence-pre-commit` (same rule set as a git pre-commit hook)
- **Canonical rules source**: `no-animal-violence` repo — rules in `action.yml` are currently duplicated inline and must be manually synced
- **MCP ecosystem**: `mcp-server-nav-language` enforces the same rule set at agent runtime; violations found by this action in audit mode feed the audit-to-dispatch pipeline (decision #37)

---

## How to Test Locally

This is a composite action — there is no local runner or unit test harness. Testing requires a real GitHub Actions run.

**Recommended test procedure:**

1. Create a test repository (or use a branch in any existing repo)
2. Add a file containing known violating phrases, for example:
   ```
   # Test file
   We killed two birds with one stone.
   This is our cash cow feature.
   The guinea pig for this rollout is the staging environment.
   ```
3. Create `.github/workflows/test-nav.yml` pointing at your branch:
   ```yaml
   name: Test NAV Action
   on: [pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: Open-Paws/no-animal-violence-action@docs/improve-documentation
           with:
             severity: warning
   ```
4. Open a PR against the test repository and inspect the Actions run
5. Verify: the display run shows all violations; the gate run fails on `warning`+; inline PR annotations appear on the correct lines

**To test severity filtering specifically:** set `severity: error` and confirm that `warning`-level patterns appear in the log but do not fail CI.

---

## Safe vs. Risky Changes

### Safe changes

- Updating documentation files (`README.md`, `AGENTS.md`, `CLAUDE.md`)
- Adding a new rule to the rule heredoc in `action.yml` that does not change existing rule names or severities
- Updating an existing rule's `alternatives` list without changing its `name` or `severity`
- Updating `note` text in any rule

### Risky changes — require testing before merge

- Changing any rule's `severity` — alters which patterns gate CI across all repos using this action
- Renaming a rule (`name` field) — may break custom configuration that references rule names
- Modifying the bash validation logic for `severity` — could introduce injection or bypass
- Modifying the Python threshold-filter snippet — could change which rules gate CI
- Changing `--disable-default-rules` flag — would expose callers to woke's built-in rule set
- Changing exit code handling — could cause the action to pass when it should fail, or fail when it should pass
- Changing the woke install step (`curl | bash`) — supply chain risk; verify the source URL before updating

### Do not do without an explicit decision

- Add new inputs to the action — existing callers may not pass the new input; use a default that preserves current behavior
- Remove or rename existing inputs — breaking change for all callers pinned to `@v1`
- Switch from composite to Docker or Node.js action — would break the "no build step" architecture principle

---

## Known Issues and TODOs

1. **Rule duplication (DRY violation)** — The 65 rules in `action.yml` are manually duplicated from the `no-animal-violence` canonical repo. Long-term goal: load rules from the canonical source at runtime. Active drift risk until resolved.
2. **No automated test harness** — Testing requires a real GitHub Actions run. A future improvement would be a matrix test workflow that runs the action against fixture files containing known violations.
3. **No named maintainer** — As of 2026-04-02, the no-animal-violence suite has no named owner. Rule updates require manual coordination.
4. **woke install via `curl | bash`** — Convenient but carries supply chain risk. Consider pinning to a specific woke release SHA once a stable release cadence is established.
5. **PR annotations require `pull-requests: write` permission** — Callers using restrictive permission sets may not see inline annotations. README documents the required permissions; the action does not enforce them.

---

## Org Decisions Affecting This Repo

- **2026-03-25**: Every Open Paws repo must run speciesist language checks on all code/docs edits. This action is the standard CI integration point.
- **2026-04-01**: Rules should eventually load from the canonical `no-animal-violence` source rather than being maintained inline. Currently a known DRY violation.
- **2026-04-11 (decision #37)**: NAV violations found during ecosystem audits auto-dispatch as agent fix tasks. This action's findings can feed that pipeline in audit mode.
