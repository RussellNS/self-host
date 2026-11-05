---
name: "crowdsec-reconciliation"
description: "Add a read-only CrowdSec evidence collector."
status: proposal
version: "v1"
---

# Add CrowdSec Evidence Collector

## Goal

Add a deterministic, read-only CrowdSec collector to the
crowdsec-reconciliation skill.

## Scope

The collector will:

- authenticate to CrowdSec LAPI using the existing watcher credential
  supplied through an environment variable
- retrieve CrowdSec alerts for the previous 24 hours
- retrieve the current active CrowdSec decisions
- normalize the collected evidence into JSON
- never expose the watcher password or bearer token in output

The collector will not:

- create, modify, or delete CrowdSec decisions
- modify Nginx, Cloudflare, or application configuration
- perform bans or unbans
- collect reverse-proxy or application logs yet
- perform reconciliation yet

## Security

The CrowdSec watcher password must be supplied through the
`CROWDSEC_WATCHER_PASSWORD` environment variable.

The authentication bearer token must exist only in memory during
collection and must never be written to output.

## Added support file

`scripts/crowdsec_collect.py`

## Verification

The proposal should be inspected and evaluated before it is applied.
