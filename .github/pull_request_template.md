<!--
Studio OS PR template (GD Works Studio).
Fill the human sections and tick what applies. The studio-os-gate runs the
deterministic checks (tests, gitleaks, Semgrep, OSV) on its own, so you do not
report those here. Keep it honest: a craftsperson signs this.
-->

## What this does
<one plain sentence: what changes for the user, and why>

**Build:** <builder>  ·  **Audit:** <auditor>
**Risk tier:** Trivial / Standard / Heavy

> The builder and the auditor are never the same person.

## Blast radius
Tick what this PR touches. The risk-router verifies these against the diff.

- [ ] auth / permissions
- [ ] payments / money
- [ ] data deletion or destructive migration
- [ ] public surface (something users see)
- [ ] none of the above

## Author checklist
- [ ] Relevant checks run locally (tests, typecheck, lint), or noted why not
- [ ] No secrets or `.env` committed
- [ ] Blast radius above is accurate
- [ ] Smallest diff that does the job, no drive-by changes

## Department gates
Leave these unticked. The reviewer signs them off before merge.

- [ ] **Heimdall, QA/QC (05):** tests pass, no regressions, behaves as described
- [ ] **Forseti, Internal Audit (10):** logic, edge cases, data integrity
- [ ] **Argus, Security (15):** secrets, dependencies, injection, vulnerabilities
- [ ] **Freyja, Design (12):** visual fidelity (only if this touches UI)
- [ ] **Tyr, External Audit (11):** only for High or Critical risk

## Notes for the reviewer
<what to look at first, tradeoffs, anything you are unsure of>

## Care
> Would a craftsperson sign this? <one line>
