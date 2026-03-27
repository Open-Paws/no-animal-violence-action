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
