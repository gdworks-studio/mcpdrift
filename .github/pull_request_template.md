<!--
Studio OS PR template (GD Works Studio).
The handoff to your reviewer, in the same shape as our Codex prompts: a metadata
header, then purpose-labelled sections. Fill the < > parts and tick what applies.
The studio-os-gate runs the deterministic checks (tests, gitleaks, Semgrep, OSV)
automatically, so you do not re-report those here. Keep it honest.
-->

# PR: <one-line title>

**Build:** <builder>   **Audit:** <auditor>   (never the same person)
**Risk tier:** Trivial / Standard / Heavy
**Blast radius:** tick what this PR touches (the reviewer and risk-router cross-check it)

- [ ] auth / permissions
- [ ] payments / money
- [ ] data deletion or destructive migration
- [ ] public surface (something users see)
- [ ] none of the above

## What this does
<plain English: what changes for the user, and why. One short paragraph.>

## How it was verified
<what you ran or checked yourself: tests, drove the app, a screenshot. The gate
covers the deterministic checks, so just add what a human actually confirmed.>

## Review focus
<where the reviewer should look first, the tradeoffs you made, anything you are
unsure of. This is what saves the auditor time.>

## Department gates
The reviewer ticks these before merge:

- [ ] **Heimdall (05), QA/QC:** tests pass, no regressions, does what it says
- [ ] **Forseti (10), Internal Audit:** logic, edge cases, data integrity
- [ ] **Argus (15), Security:** secrets, dependencies, injection, vulnerabilities
- [ ] **Freyja (12), Design:** visual fidelity (only if it touches UI)
- [ ] **Tyr (11), External Audit:** only for High or Critical risk

## Care
> Would a craftsperson sign this? <one honest line>
