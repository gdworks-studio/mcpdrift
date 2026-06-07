#!/usr/bin/env python3
"""Studio OS risk-router — blast-radius classifier for the pre-merge gate.

Flags high-blast-radius surfaces (auth, payments, data-deletion, migrations,
RLS) in a PR. Answers the studio question "flag anything touching auth,
payments, or deletions" — architecture, not style.

It classifies on BOTH the changed file paths AND the added diff lines, so
sensitive logic dropped into a neutrally named file is still caught.

Hard rule the pilot enforces on its own: a changed migration that runs a
destructive statement must carry an acknowledging `-- rollback:`/`-- care:`
note NEAR that statement. Other surfaces are labelled and raise the risk tier
for the reviewer + auditor.

Fail-closed: if the base ref cannot be resolved, the script errors (exit 2)
rather than silently reporting "no changes."

Usage: risk_router.py <base_ref>   (empty/"origin/" falls back to origin/main)
"""

import json
import os
import re
import subprocess
import sys

SURFACES = {
    "auth / permissions / RLS": re.compile(r"auth|permission|role|rls|policy|session|jwt|token", re.I),
    "payments / money": re.compile(r"payment|receipt|refund|void|invoice|billing|price|stripe|revenuecat", re.I),
    "data deletion": re.compile(r"delete|destroy|purge|account[-_]?deletion|erase|drop\s+table", re.I),
    "migrations": re.compile(r"(supabase/migrations/.*\.sql|priv/repo/migrations/.*\.exs)$", re.I),
}
REQUIRED_REVIEW = {
    "auth / permissions / RLS": "Argus + Heimdall",
    "payments / money": "Heimdall domain-risk + Forseti",
    "data deletion": "Atlas + Argus",
    "migrations": "Atlas migration-safety + rollback note",
}

DESTRUCTIVE = re.compile(r"\b(drop\s+(table|column|schema|view)|drop_if_exists|truncate|delete\s+from|remove\s*(\(|:))", re.I)
ACK_NOTE = re.compile(r"(--|#)\s*(rollback|care):", re.I)
ACK_WINDOW = 3  # lines around a destructive statement that may carry its note

# Content scanning runs only on real source files, and never on the gate's own
# config under .github/ — otherwise the router flags itself (its pattern list
# literally contains "auth"/"payment"/"delete"). Over-labelling user code is
# safe; under-labelling is the risk we are guarding against.
CODE_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".sql", ".go", ".rb", ".py", ".ex", ".exs", ".heex", ".eex", ".rs", ".dart")


def git(args):
    """Run a git command; return (ok, stdout)."""
    p = subprocess.run(["git"] + args, capture_output=True, text=True)
    return p.returncode == 0, p.stdout


def resolve_base(base_ref):
    """Return a base ref that actually resolves, or None (fail-closed signal).

    Empty / 'origin/' (e.g. workflow_dispatch has no base_ref) falls back to
    origin/main. The chosen ref must pass `git rev-parse --verify`."""
    candidates = []
    if base_ref and base_ref.rstrip("/") not in ("", "origin"):
        candidates.append(base_ref)
    candidates += ["origin/main", "main"]
    for ref in candidates:
        ok, _ = git(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
        if ok:
            return ref
    return None


def changed_files(base):
    ok, out = git(["diff", "--name-only", f"{base}...HEAD"])
    if not ok:
        ok, out = git(["diff", "--name-only", base])
    return [f for f in out.splitlines() if f.strip()]


def added_lines_by_file(base):
    """Map file -> list of added content lines (diff '+' lines, excluding '+++')."""
    ok, out = git(["diff", "--unified=0", f"{base}...HEAD"])
    if not ok:
        ok, out = git(["diff", "--unified=0", base])
    result, current = {}, None
    for line in out.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            result.setdefault(current, [])
        elif line.startswith("+") and not line.startswith("+++") and current:
            result[current].append(line[1:])
    return result


def classify(files, added):
    hits = {label: set() for label in SURFACES}
    for f in files:  # path-based
        for label, pattern in SURFACES.items():
            if pattern.search(f):
                hits[label].add(f)
    for f, lines in added.items():  # content-based (added lines only)
        if f.startswith(".github/") or not f.endswith(CODE_EXT):
            continue
        blob = "\n".join(lines)
        for label, pattern in SURFACES.items():
            if label == "migrations":
                continue  # migrations are path-defined, not content-sniffed
            if pattern.search(blob):
                hits[label].add(f)
    return {label: sorted(paths) for label, paths in hits.items() if paths}


def unacknowledged_destructive(files):
    """A destructive statement needs an ack note within ACK_WINDOW lines."""
    offenders = []
    for f in files:
        if not SURFACES["migrations"].search(f) or not os.path.exists(f):
            continue
        lines = open(f, encoding="utf-8", errors="replace").read().splitlines()
        for i, line in enumerate(lines):
            if not DESTRUCTIVE.search(line):
                continue
            lo, hi = max(0, i - ACK_WINDOW), min(len(lines), i + ACK_WINDOW + 1)
            if not any(ACK_NOTE.search(l) for l in lines[lo:hi]):
                offenders.append(f"{f}:{i + 1}")
    return offenders


def write_summary(lines):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        print("\n".join(lines))
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main():
    raw_base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    base = resolve_base(raw_base)
    if base is None:
        print(f"risk-router: cannot resolve a base ref from '{raw_base}' "
              "(tried it, origin/main, main). Failing closed.", file=sys.stderr)
        return 2

    files = changed_files(base)
    added = added_lines_by_file(base)
    hits = classify(files, added)
    offenders = unacknowledged_destructive(files)

    tier = "High" if hits else "Standard"
    report = {"base": base, "changed": len(files), "tier": tier,
              "surfaces": hits, "destructive_migrations_unacknowledged": offenders}
    with open("risk-router.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    out = ["## Studio OS — risk-router", "",
           f"**Risk tier:** {tier}  ·  **base:** {base}  ·  **files changed:** {len(files)}", ""]
    if hits:
        out += ["| Surface | Required review | Files |", "|---|---|---|"]
        for label, paths in hits.items():
            shown = ", ".join(paths[:4]) + (" …" if len(paths) > 4 else "")
            out.append(f"| {label} | {REQUIRED_REVIEW[label]} | {shown} |")
    else:
        out.append("No high-blast-radius surfaces touched.")
    write_summary(out)

    if offenders:
        msg = ["", "### ❌ Destructive migration without a nearby rollback/care note:"]
        msg += [f"- `{o}` — add `-- rollback:` or `-- care:` within {ACK_WINDOW} lines, explaining intent + recovery." for o in offenders]
        write_summary(msg)
        print("risk-router: destructive migration(s) lack a nearby note:",
              ", ".join(offenders), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
