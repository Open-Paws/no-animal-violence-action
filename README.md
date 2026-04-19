# No Animal Violence — GitHub Action

[![No Animal Violence](https://img.shields.io/badge/language-no--animal--violence-green)](https://github.com/Open-Paws/no-animal-violence)
[![Part of Open Paws](https://img.shields.io/badge/Open%20Paws-ecosystem-brightgreen)](https://openpaws.ai)
[![Status: Production](https://img.shields.io/badge/status-production-brightgreen)](./AGENTS.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)
[![Composite Action](https://img.shields.io/badge/type-composite%20action-lightgrey)](./action.yml)
[![Scan: 65+ patterns](https://img.shields.io/badge/patterns-65%2B-orange)](./action.yml)

A composite GitHub Action that scans pull requests and repository files for speciesist language — violent animal idioms, commodity framing, and industry euphemisms — and fails CI when violations meet or exceed a configured severity threshold. Part of the [Open Paws](https://openpaws.ai) no-animal-violence tooling suite.

> [!NOTE]
> This project is part of the [Open Paws](https://openpaws.ai) ecosystem — AI infrastructure for the animal liberation movement. [Explore the full platform →](https://github.com/Open-Paws)

---

## Quickstart

Add this file to your repository as `.github/workflows/inclusive-language.yml`:

```yaml
name: Inclusive Language
on: [pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write  # required for inline PR annotations
      checks: write
    steps:
      - uses: actions/checkout@v4
      - uses: Open-Paws/no-animal-violence-action@v1
```

That is the complete integration. The action uses a self-contained Python scanner with no external binary dependencies — no install step required.

To configure severity or limit scan scope:

```yaml
- uses: Open-Paws/no-animal-violence-action@v1
  with:
    severity: warning   # error | warning | info (default: warning)
    paths: docs/ src/   # space-separated paths (default: .)
```

---

## Features

### Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `severity` | No | `warning` | Minimum severity that fails CI. Accepts `error`, `warning`, or `info`. Lower values catch fewer patterns; higher values catch more. |
| `paths` | No | `.` | Space-separated list of paths to scan. Limit scope to `docs/` or `src/` to reduce noise. |
| `github-token` | No | `${{ github.token }}` | Token used to post inline PR annotations. The default repository token is sufficient in most cases. |

### Severity levels

| Level | Typical patterns | Examples |
|-------|-----------------|---------| 
| `error` | Direct references to harming or killing animals | "kill two birds with one stone", "like a chicken with its head cut off", "bring home the bacon" |
| `warning` | Industry commodity framing and animal-as-object metaphors | "livestock", "guinea pig", "cash cow", "processing plant", "gestation crate" |
| `info` | Common idioms flagged for awareness | "red herring", "pet project", "hold your horses", "canary in a coal mine" |

Setting `severity: error` is the most permissive gate — it only blocks merges on the most harmful patterns. Setting `severity: info` blocks on all 65+ detected patterns.

### What the action checks

Three categories of patterns, all embedded inline in `scan.py`:

- **Violent animal idioms** — phrases that reference harm to animals (e.g., "beat a dead horse" → "belabor the point")
- **Animal-as-object metaphors** — phrases that reduce animals to instruments or commodities (e.g., "guinea pig" → "test subject", "cash cow" → "profit center")
- **Industry euphemisms** — terms that obscure the reality of farmed animal treatment (e.g., "processing plant" → "slaughterhouse", "livestock" → "farmed animals")

### Outputs

This action produces no explicit step outputs. Results are communicated through:

- **CI pass/fail** — exits non-zero when violations at or above the severity threshold are found
- **Workflow log** — a full scan always appears in the log, showing every violation regardless of threshold
- **PR annotations** — inline comments appear on the relevant lines in the PR diff (requires `pull-requests: write` permission)

### Configuration examples

Only fail on the most severe patterns:

```yaml
- uses: Open-Paws/no-animal-violence-action@v1
  with:
    severity: error
```

Scan documentation only:

```yaml
- uses: Open-Paws/no-animal-violence-action@v1
  with:
    severity: warning
    paths: docs/ README.md
```

Full strictness — fail on all patterns:

```yaml
- uses: Open-Paws/no-animal-violence-action@v1
  with:
    severity: info
    paths: .
```

Full CI integration with explicit permissions:

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
      pull-requests: write
      checks: write
    steps:
      - uses: actions/checkout@v4
      - uses: Open-Paws/no-animal-violence-action@v1
        with:
          severity: warning
          paths: .
```

---

## Documentation

- [AGENTS.md](./AGENTS.md) — Architecture details, execution flow, safe vs. risky changes, and guidance for automated contributors
- [action.yml](./action.yml) — The complete action definition: inputs and run steps
- [scan.py](./scan.py) — The self-contained Python scanner: all 65+ rules and scan logic
- [no-animal-violence](https://github.com/Open-Paws/no-animal-violence) — Canonical rule dictionary (source of truth for all patterns)
- [Open Paws ecosystem](https://github.com/Open-Paws) — Related tools and platform repos

---

<details>
<summary>Architecture</summary>

### Action type

Composite action — no Docker image, no Node.js runtime. All steps run in bash and Python 3, which are pre-installed on all GitHub-hosted runners. This keeps the action fast (no container pull, no binary install) and avoids supply chain risk from third-party install scripts.

### Execution flow

```text
Step 1: Verify Python 3
  └── python3 --version  (fail fast if unavailable)

Step 2: Scan
  └── python3 "$GITHUB_ACTION_PATH/scan.py"
      ├── Reads INPUT_PATHS (default: ".")
      ├── Reads INPUT_SEVERITY (default: "warning")
      ├── Loads .wokeignore patterns from cwd
      ├── Walks file tree, emits ::error/::warning/::notice annotations
      └── Exits 1 if any finding at or above severity threshold
```

### Severity ordering

Severity values are ordered: `error` (0) > `warning` (1) > `info` (2). The threshold check keeps findings where `order[finding.severity] <= order[threshold]`:

- `severity: error` → only `error` findings gate CI
- `severity: warning` → `error` and `warning` findings gate CI
- `severity: info` → all findings gate CI

### Security design

- The `severity` input is validated against an explicit allowlist (`error`, `warning`, `info`) in Python before use, passed via environment variable — never interpolated into shell
- No external binary downloads — the scanner is a single Python file checked into the repository
- Supply chain risk from `curl | bash` is eliminated entirely
- `.wokeignore` is respected to exclude rule definition files from self-scanning

### Known limitations

- Rules in `scan.py` are maintained inline and must be manually kept in sync with the canonical `no-animal-violence` dictionary — rule drift is an active maintenance risk
- No automated test harness — testing requires a real GitHub Actions run against a fixture repository
- PR annotations require `pull-requests: write` permission — callers with restrictive permission sets may not see inline annotations

</details>

---

## Contributing

Contributions to `no-animal-violence-action` are welcome — especially rule additions, severity calibration, and test infrastructure.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-change`)
3. Make changes to `scan.py` for rule changes, or `action.yml` for workflow changes
4. Test by pointing a workflow in a separate test repository at your branch (`Open-Paws/no-animal-violence-action@your-branch`) and opening a PR against fixture files containing known violations
5. Submit a pull request — this repo runs itself as a CI check, so your PR is scanned automatically

When adding or modifying rules in `scan.py`, also update the canonical dictionary in [no-animal-violence](https://github.com/Open-Paws/no-animal-violence) to keep the suite in sync.

For architecture context, safe vs. risky change guidance, and notes for automated contributors, see [AGENTS.md](./AGENTS.md).

---

## License and Acknowledgments

MIT — Copyright (c) 2026 [Open Paws](https://openpaws.ai), a 501(c)(3) nonprofit.

The language patterns are grounded in research on speciesist framing in natural language:

- Hagendorff et al. (2023). "Speciesist bias in AI." *AI and Ethics*. Documents how animal-harm metaphors encode speciesist defaults in language models.
- Takeshita et al. (2022). *Information Processing & Management*. Examines how commodity framing shapes perception of farmed animals.
- Leach et al. (2023). *British Journal of Social Psychology*. Analyzes how figurative language normalizes attitudes toward animal exploitation.

---

<!-- tech_stack: bash, python3, yaml -->
<!-- project_status: production -->
<!-- difficulty: beginner -->
<!-- skill_tags: github-actions, inclusive-language, speciesism, ci-cd, linting -->
<!-- related_repos: no-animal-violence, no-animal-violence-pre-commit, reviewdog-no-animal-violence, semgrep-rules-no-animal-violence, eslint-plugin-no-animal-violence, vale-no-animal-violence, vscode-no-animal-violence -->

---

[Donate](https://openpaws.ai/donate) · [Discord](https://discord.gg/openpaws) · [openpaws.ai](https://openpaws.ai) · [Volunteer](https://openpaws.ai/volunteer)
