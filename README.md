# NEXOVIA Marketing Master

Public application code for the NEXOVIA digital-product pilot.

## Current scope

The first implementation slice is a dependency-free approval-policy kernel. It verifies that a human approval:

- is active and not expired;
- permits the exact action and resource;
- matches the immutable content version;
- does not exceed its cost ceiling.

It intentionally performs no external calls and stores no personal data or secrets.

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Security

Never commit API keys, passwords, tokens, private keys, production data, interview contacts, or internal project-governance documents. Use synthetic test data only.

