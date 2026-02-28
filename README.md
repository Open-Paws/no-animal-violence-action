# No Animal Violence — GitHub Action

A GitHub Action that scans PRs and documentation for speciesist language and suggests clearer, more professional alternatives.

## Quick Start

Add to `.github/workflows/inclusive-language.yml`:

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

## What It Detects

- **Violent animal idioms**: "kill two birds with one stone" → "accomplish two things at once"
- **Animal-as-object metaphors**: "guinea pig" → "test subject", "sacred cow" → "unquestioned belief"
- **Technical terminology**: "cattle vs. pets" → "ephemeral vs. persistent", "canary deployment" → "progressive rollout"

## Configuration

```yaml
- uses: Open-Paws/no-animal-violence-action@v1
  with:
    severity: warning    # minimum severity: error, warning, info
    paths: docs/ src/    # paths to scan (default: entire repo)
```

## Academic Foundation

- Hagendorff et al. (2023). "Speciesist bias in AI." *AI and Ethics*.
- Takeshita et al. (2022). *Information Processing & Management*.
- Leach et al. (2023). *British Journal of Social Psychology*.

## License

MIT — [Open Paws](https://openpaws.ai)
