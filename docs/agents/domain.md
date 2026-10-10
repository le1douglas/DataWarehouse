# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`GLOSSARY-MAP.md`** at the repo root: it points at the one glossary of this repo, `docs/GLOSSARY.md`. Read that file.
- **`docs/adr/`**: read ADRs that touch the area you're about to work in.

There is no `GLOSSARY.md` at the repo root, and none should be created there: new and changed terms go in `docs/GLOSSARY.md`.

If `docs/adr/` doesn't exist, **proceed silently**. Don't flag its absence; don't suggest creating it upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates it lazily when a decision actually gets resolved.

## File structure

```
/
├── GLOSSARY-MAP.md                    ← points at docs/GLOSSARY.md
├── docs/
│   ├── GLOSSARY.md
│   └── adr/
│       └── 0001-audit-view-created-by-on-run-end-macro.md
└── src/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `docs/GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_
