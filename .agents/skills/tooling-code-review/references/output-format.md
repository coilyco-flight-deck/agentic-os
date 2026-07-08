# Output format

Return exactly one review object with these fields.

```text
verdict: pass|block
confidence: high|medium|low
summary: <1-3 sentences>
findings:
  - severity: critical|high|medium|low
    file: <path or n/a>
    line: <line or n/a>
    problem: <what is wrong>
    impact: <why it matters>
conclusion: <short paragraph fit for a final WARD-OUTCOME comment>
```

Rules:

- Order findings by severity, highest first.
- Include file and line references when possible.
- Keep `summary` concise and concrete.
- Use `verdict: pass` only after a deliberate refutation pass.
- Use `verdict: block` for correctness gaps, contract mismatches, missing coverage, or review uncertainty that needs another worker change.
- The conclusion should be a brief human-readable wrap-up, not a restatement of the whole review.
