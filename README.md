# NEXOVIA Marketing Master

Public application code for the NEXOVIA digital-product pilot.

## Current scope

The runtime currently contains two dependency-free, fail-closed domain kernels:

1. An approval policy that verifies that a human approval:

- is active and not expired;
- permits the exact action and resource;
- matches the immutable content version;
- does not exceed its cost ceiling.

2. A product-agent policy that:

- enforces exactly one agent identity per product;
- isolates product characteristics, target groups, and marketing strategies;
- requires evidence for verified statements and labels unsupported hypotheses;
- blocks unapproved cross-product evidence;
- refuses product, claim, publishing, campaign, permission, and budget approvals;
- enforces brief, cost, time, identity, and schema boundaries.

It intentionally performs no external calls and stores no personal data or secrets.

## Run tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Security

Never commit API keys, passwords, tokens, private keys, production data, interview contacts, or internal project-governance documents. Use synthetic test data only.
