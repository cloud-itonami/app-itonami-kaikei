---
name: kaikei-kakutei
description: Preview a Japanese personal income tax worksheet, check journal and evidence history, and explain the manual filing checklist using a local synthetic ledger.
compatibility: Requires a trusted local host with explicit permission to use the kaikei-mcp stdio server for tool calls.
---

# Kaikei 確定申告

Importing this skill provides instructions. The host retains consent, tool permissions, and local process settings. To enable tools, a user may add the adjacent `mcp.json.example` to their local host after review and make the repository's `bin/kaikei-mcp` available on PATH.

Use a synthetic ledger and synthetic evidence. Keep real tax returns, personal numbers, credentials and source files in the user's local browser. Maintain one stdio connection for a worksheet. The process holds its worksheet in memory until stdin closes.

1. Call `taxreturn.read_state` to discover the schema and current operation definitions.
2. Use `ledger.import` with a synthetic `kaikei.ledger.v1` object and the selected year. Use `income.classify` based on categories the user supplied. Use `adjustment.draft` for balanced journal entries the user supplied.
3. Use `taxreturn.preview_draft` with the user's confirmed scenario inputs. If the host opens a fresh process for each call, pass the synthetic ledger, year, classifications and optional adjustments to this operation. Report the result as an estimate and keep missing jurisdiction fields marked `未対応`. Show the JSON result if the host has no MCP Apps support.
4. Direct internal approval and history corrections to two different people in the local browser. Keep `adjudicating: false` and `submission-status: user-manual-required`. Leave signing, final filing decisions and submission with the individual.
