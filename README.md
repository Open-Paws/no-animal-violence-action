# No Animal Violence — GitHub Action

[![No Animal Violence](https://img.shields.io/badge/language-no--animal--violence-green)](https://github.com/Open-Paws/no-animal-violence)
[![Part of Open Paws](https://img.shields.io/badge/Open%20Paws-ecosystem-brightgreen)](https://openpaws.ai)
[![Status: Production](https://img.shields.io/badge/status-production-brightgreen)](./)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

A composite GitHub Action that scans pull requests and documentation for speciesist language and suggests clearer, more professional alternatives. Part of the [Open Paws](https://openpaws.ai) no-animal-violence tooling suite.

---

## What It Does

When added to a GitHub Actions workflow, this action:

1. Installs [woke](https://github.com/get-woke/woke) — an inclusive language linter
2. Generates a rule file containing 65+ animal-violence language patterns, organized by severity
3. Runs a full scan so all violations appear in the CI log
4. Runs a second severity-filtered scan and **fails CI** when violations meet or exceed the configured threshold
5. Posts inline PR annotations so reviewers see the exact line and a suggested alternative

It enforces three categories of patterns:

- **Violent animal idioms** — phrases that reference harm to animals (e.g., "like a chicken with its head cut off" → "in a panic")
- **Animal-as-object metaphors** — phrases that reduce animals to instruments or commodities (e.g., "guinea pig" → "test subject", "cash cow" → "profit center")
- **Industry euphemisms** — terms that obscure the reality of farmed animal treatment (e.g., "processing plant" → "slaughterhouse", "livestock" → "farmed animals")

---

## Quick Start

Create `.github/workflows/inclusive-language.yml` in your repository:

```yaml
name: Inclusive Language
on: [pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Open-Paws/no-animal-violence-action@v1
```

That is all that is required for a default run. It will scan the entire repository and fail CI on any `warning`-level or higher violation.

---

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `severity` | No | `warning` | Minimum severity that will fail CI. Accepts `error`, `warning`, or `info`. Lower severity thresholds catch more patterns. |
| `paths` | No | `.` | Space-separated list of paths to scan. Useful for limiting scope to `docs/` or `src/`. |
| `github-token` | No | `${{ github.token }}` | GitHub token used to post PR annotations. The default token is sufficient in most cases. |

### Severity Levels Explained

The action uses a three-tier severity scale:

| Level | Typical patterns | Example |
|-------|-----------------|---------|
| `error` | Directly references killing or harming an animal | "kill two birds with one stone", "like a chicken with its head cut off" |
| `warning` | Industry commodity framing or animal-as-object metaphors | "livestock", "guinea pig", "cash cow", "sacred cow" |
| `info` | Common idioms flagged for awareness only | "red herring", "pet project", "hold your horses" |

Setting `severity: error` is the most permissive gate — it only blocks merges on the most harmful patterns. Setting `severity: info` blocks on all detected patterns.

---

## Outputs

This action produces no explicit step outputs. It communicates results through:

- **CI pass/fail** — exits non-zero when violations at or above the severity threshold are found
- **Workflow log** — a full scan run always appears in the log, showing every violation regardless of threshold
- **PR annotations** — inline comments appear on the relevant lines in the PR diff (requires the `github-token` input)

---

## Configuration Examples

### Only fail on errors (most permissive)

```yaml
- uses: Open-Paws/no-animal-violence-action@v1
  with:
    severity: error
```

### Scan documentation only

```yaml
- uses: Open-Paws/no-animal-violence-action@v1
  with:
    severity: warning
    paths: docs/ README.md
```

### Full strictness — fail on all patterns including info-level

```yaml
- uses: Open-Paws/no-animal-violence-action@v1
  with:
    severity: info
    paths: .
```

### Using an explicit token (e.g., for cross-repo annotation)

```yaml
- uses: Open-Paws/no-animal-violence-action@v1
  with:
    severity: warning
    github-token: ${{ secrets.MY_PAT }}
```

---

## Example Workflow — Full CI Integration

```yaml
name: Language Quality
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  inclusive-language:
    name: No Animal Violence Check
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write   # needed for inline PR annotations
      checks: write
    steps:
      - uses: actions/checkout@v4
      - uses: Open-Paws/no-animal-violence-action@v1
        with:
          severity: warning
          paths: .
```

---

## Example CI Output

When a violation is found, the full scan log will show:

```
docs/architecture.md:14:32: [warning] Rule: livestock
  Found: "livestock"
  Suggestions: "farmed animals", "animals raised for food"

src/components/README.md:7:10: [error] Rule: guinea-pig
  Found: "guinea pig"
  Suggestions: "test subject", "first to try", "early adopter"
```

The PR annotation will appear inline on the violating line with the same suggestion text.

When no violations are found at or above the threshold:

```
No rules at severity 'warning' or above — scan passed.
```

---

## How It Works (Architecture)

The action is a **composite action** with no Docker container and no Node.js runtime. All logic runs in bash and Python 3, which are available on all GitHub-hosted runners.

### Execution steps

1. **Install woke** — downloads the woke binary from the official release channel via `curl | bash` into `/usr/local/bin`
2. **Generate rule file** — writes 65+ pattern rules to `/tmp/.woke.yaml` as a heredoc; no external network call is needed for the rules themselves
3. **Display run** — runs `woke` against all specified paths with `--disable-default-rules` so only the generated rules apply; exit code is ignored so all violations appear in the log
4. **Threshold filter** — a Python 3 snippet reads the generated rule file and writes `/tmp/.woke-threshold.yaml` containing only rules at or above the requested severity; exits 99 if no rules match the threshold (nothing to gate on)
5. **Gate run** — runs `woke` again against the threshold-filtered config with `--exit-1-on-failure`; CI fails if any violations are found

### Security notes

- The `severity` input is validated against an explicit allowlist (`error|warning|info`) in bash before use, and passed to Python via environment variable — never interpolated into source
- The Python fallback uses a strict sentinel (`-1`) rather than a silent default, so an unrecognized severity value surfaces as a CI error rather than passing silently
- `--disable-default-rules` is applied on both woke runs so woke's built-in rule set (which includes its own `whitelist/blacklist` rule at warning level) cannot interfere with the severity filter

---

## Relationship to the No-Animal-Violence Ecosystem

This action is part of a broader suite of tools enforcing the same canonical rule set:

| Tool | Use case |
|------|----------|
| [no-animal-violence](https://github.com/Open-Paws/no-animal-violence) | Canonical rule dictionary — source of truth for all 65+ patterns |
| **no-animal-violence-action** (this repo) | GitHub Actions CI — catches violations in PRs before merge |
| [no-animal-violence-pre-commit](https://github.com/Open-Paws/no-animal-violence-pre-commit) | Local git hook — catches violations before a commit is created |
| [reviewdog-no-animal-violence](https://github.com/Open-Paws/reviewdog-no-animal-violence) | Alternative reviewdog-based CI action |
| [semgrep-rules-no-animal-violence](https://github.com/Open-Paws/semgrep-rules-no-animal-violence) | Semgrep-based CI scanner with AST-level matching |
| [eslint-plugin-no-animal-violence](https://github.com/Open-Paws/eslint-plugin-no-animal-violence) | ESLint plugin for JavaScript/TypeScript projects |
| [vale-no-animal-violence](https://github.com/Open-Paws/vale-no-animal-violence) | Vale rules for documentation prose |
| [vscode-no-animal-violence](https://github.com/Open-Paws/vscode-no-animal-violence) | VS Code extension for editor-time feedback |

**Important:** The 65 rules embedded in `action.yml` are currently maintained inline and must be kept in sync with the canonical `no-animal-violence` dictionary manually. Rule drift between these two repositories is an active maintenance risk. A long-term goal is to load rules from the canonical source at action runtime rather than duplicating them.

---

## Academic Foundation

The language choices enforced by this action are grounded in peer-reviewed research:

- Hagendorff et al. (2023). "Speciesist bias in AI." *AI and Ethics*. Documents how animal-harm metaphors encode speciesist defaults in language models.
- Takeshita et al. (2022). *Information Processing & Management*. Examines how commodity framing shapes perception of farmed animals.
- Leach et al. (2023). *British Journal of Social Psychology*. Analyzes how figurative language normalizes attitudes toward animal exploitation.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-change`)
3. Make changes to `action.yml` (the composite action definition)
4. Test by adding the action to a workflow in a separate test repository containing known violating phrases
5. Submit a pull request — this repo runs itself as a CI check, so your PR will be scanned automatically

When adding or modifying rules in `action.yml`, also update the canonical dictionary in [no-animal-violence](https://github.com/Open-Paws/no-animal-violence) to keep the suite in sync.

See [AGENTS.md](./AGENTS.md) for architecture details and guidance for automated contributors.

---

MIT — [Open Paws](https://openpaws.ai)
