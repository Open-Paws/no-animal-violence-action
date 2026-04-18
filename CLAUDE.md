# No Animal Violence — GitHub Action

GitHub Action that scans pull requests and documentation for speciesist language and suggests clearer, professional alternatives. Part of the [No Animal Violence](https://github.com/Open-Paws) speciesist language detection suite for Open Paws.

## Quick Start

```bash
# No local build needed — this is a composite GitHub Action.
# To test, add the action to a workflow in any repo:

# .github/workflows/inclusive-language.yml
name: Inclusive Language
on: [pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Open-Paws/no-animal-violence-action@v1
```

## Architecture

This is a **composite GitHub Action** (no Docker, no Node runtime). It:

1. Installs [woke](https://github.com/get-woke/woke) — an inclusive language linter
2. Generates a `.woke.yaml` rule file with 65 animal-violence language rules
3. Runs woke against specified paths
4. Posts inline PR annotations via reviewdog

Rules are organized by severity (`error`, `warning`, `info`) and category (violent idioms, animal-as-object metaphors, technical terminology).

## Key Files

| File | Description |
|------|-------------|
| `action.yml` | Composite action definition — inputs, rule generation, scanning steps (~950 lines) |
| `README.md` | Usage docs, configuration options, academic references |
| `LICENSE` | MIT license |

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `severity` | `warning` | Minimum severity to report (`error`, `warning`, `info`) |
| `paths` | `.` | Paths to scan (space-separated) |
| `github-token` | `${{ github.token }}` | Token for PR annotations |

## Organizational Context

**Strategic role (Lever 1 + Lever 3):** Drop-in GitHub Action CI integration — primary CI enforcement mechanism for the no-animal-violence suite. Catches speciesist phrases before they merge into any repo's main branch. Composite action using woke + reviewdog.

**Current org priorities relevant to this repo:**
- Should be added to `open-paws-platform` CI and templated into the new-repo cookiecutter. See `ecosystem/integration-todos.md` §27a and §29.
- Suite maintenance has **no named owner** as of 2026-04-02. The 65 rules embedded inline in `action.yml` need to stay in sync with the `no-animal-violence` canonical dictionary — rule drift is an active risk.

**Decisions affecting this repo:**
- 2026-03-25: Every org repo must run speciesist language checks on all code/docs edits. This action is the standard CI integration point.
- 2026-04-01: Rules embedded in `action.yml` should eventually load from the `no-animal-violence` canonical source rather than being maintained inline. Currently duplicated — this is a known DRY violation and drift risk.

## Related Repos

- [no-animal-violence](https://github.com/Open-Paws/no-animal-violence) — Canonical rule dictionary (rules currently duplicated inline in `action.yml`)
- [reviewdog-no-animal-violence](https://github.com/Open-Paws/reviewdog-no-animal-violence) — Alternative reviewdog-based action
- [no-animal-violence-pre-commit](https://github.com/Open-Paws/no-animal-violence-pre-commit) — Local git hook (complements this action)
- [semgrep-rules-no-animal-violence](https://github.com/Open-Paws/semgrep-rules-no-animal-violence) — Alternative CI scanner using Semgrep

## Development Standards

### 10-Point Review Checklist (ranked by AI violation frequency)

1. **DRY** — 65 rules in `action.yml` are duplicated from `no-animal-violence`. Any rule change must update both. This is the primary DRY violation to fix long-term.
2. **Deep modules** — The action's interface (3 inputs) is simpler than the ~950-line implementation. Keep it that way.
3. **Single responsibility** — Rule generation, scanning, and annotation are three distinct steps. Don't collapse them.
4. **Error handling** — The action must fail the CI check on severity matches, not silently pass. Verify exit code behavior.
5. **Information hiding** — Users need only know the three inputs. Internal rule generation is an implementation detail.
6. **Ubiquitous language** — use "farmed animal" not the industry commodity term, "factory farm" not the euphemism. Never introduce synonyms in rule messages.
7. **Design for change** — Adding a rule should require only updating the canonical source. Inline duplication makes changes expensive.
8. **Legacy velocity** — Before modifying rule generation logic, test against a real PR in a test repo.
9. **Over-patterning** — Composite action (no Docker, no Node) is the right architecture. Don't add a build step.
10. **Test quality** — Test by adding the action to a PR containing known phrases. Verify annotations appear at the correct line.

### Quality Gates

- **Test in a real repo**: Add to a PR with known phrases, verify annotations appear correctly.
- **Desloppify**: `desloppify scan --path .` — minimum score ≥85.
- **Two-failure rule**: After two failed fixes on the same problem, stop and restart.

### Seven Concerns — Repo-Specific Notes

1. **Testing** — Manual testing against real PRs. No automated test harness.
2. **Security** — Runs with `github.token`. Verify it requests only the permissions needed for PR annotations (read PRs, write checks).
3. **Privacy** — Scans PR diff content in CI. No retention beyond the CI run.
4. **Cost optimization** — Composite action (no Docker pull) is fast and cheap. Keep it that way.
5. **Advocacy domain** — Rule messages must use movement-standard language in suggestions.
6. **Accessibility** — PR annotations must be clear and actionable to developers unfamiliar with advocacy context.
7. **Emotional safety** — Rule messages explain the alternative, not the harm in detail.

### Structured Coding Reference

For tool-specific AI coding instructions (Claude Code rules, Cursor MDC, Copilot, Windsurf, etc.), copy the corresponding directory from `structured-coding-with-ai` into this project root.

## MCP Integrations (live 2026-04-09)

The broader NAV suite this action belongs to now has live MCP infrastructure that complements CI scanning:

- **mcp-server-nav-language** — Pure regex MCP server (sub-10ms) enforcing the same 65-rule pattern set at agent runtime via Gary MCP hub Phase 3. This action catches violations in PRs; the MCP server catches them in agent-generated content before it reaches a PR.
- **lbr8-mcp-constraints** — Bundles 12 offline NAV patterns from this suite as `StaticConstraintSource` middleware for any MCP tool handler.
- **mcp-server-aha-evaluation** — Uses NAV rules as Stage 1 of a two-stage content evaluation pipeline.
- **Audit-to-dispatch (decision #37, 2026-04-11)** — NAV violations found during ecosystem audits now auto-dispatch as agent fix tasks. This action's findings feed that pipeline when run in audit mode.

## Decisions Reviewed

Last reviewed: 2026-04-11 (decisions #37 audit-to-dispatch, mcp-server-nav-language live)
