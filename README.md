# hermes-plugin-brain

A lightweight, file-based knowledge graph for [Hermes Agent](https://github.com/NousResearch/hermes-agent) —
a "brain" of durable project/domain facts that gets injected into every turn,
so the agent doesn't relearn the same lessons every session.

## What it does

- Stores knowledge as small markdown nodes (`projects/`, `domains/`,
  `decisions/`, `lessons/`), each with a handful of **anchors**: one-line
  facts with a pointer (`<fact> ⇒ path:line` / `⇒ skill name chNN` / `⇒ doc`).
- Before every LLM call, searches the graph (FTS5 over an on-disk SQLite
  index) and injects the top ~5 relevant anchors as context — no LLM call
  needed for retrieval, it's pure keyword search + a small graph walk.
- Ships a `brain` CLI (`bin/brain`, stdlib-only Python) for maintaining the
  graph: `new`, `add`, `inbox`, `review`, `search`, `lint`, `graph`, `link`,
  `related`, `merge`.
- A `/brain <subcommand>` slash command in Hermes wraps the same CLI.

See `SCHEMA.md` (installed into your data dir on first run) for the node
format and authoring rules.

## Install

```bash
hermes plugins install <this-repo-url>
hermes plugins enable brain
```

That's it — no extra setup step. On first load, the plugin notices its data
directory (`$HERMES_HOME/brain` by default) doesn't exist yet and seeds it
from the bundled `_bootstrap/` template (empty node directories + `SCHEMA.md`
+ the `brain` CLI). Nothing is overwritten on subsequent loads or plugin
updates — your accumulated graph is safe.

## Data directory layout (created on first run)

```
$HERMES_HOME/brain/
├── bin/brain          # the CLI (stdlib only, no deps)
├── SCHEMA.md           # node format + authoring rules
├── brain.db            # SQLite FTS5 index (gitignored, rebuilt via `brain index`)
├── domains/            # cross-cutting knowledge (a technology, a recurring theme)
├── projects/            # facts scoped to one project/repo
├── decisions/           # "we chose X over Y because Z" records
├── lessons/             # mistakes made once, not to repeat
├── pages/ journals/     # free-form notes (logseq-style, optional)
├── index.md, log.md, _inbox.md
```

`$HERMES_HOME` defaults to `~/.hermes` (or your active Hermes profile
directory); override with the `BRAIN_HOME` env var if you want the graph to
live somewhere else.

## Using it

Once enabled, brain works passively — every user message triggers a search
and (if relevant anchors exist) a small context block gets injected before
the LLM call. You don't have to do anything for retrieval.

To add knowledge:

```bash
$HERMES_HOME/brain/bin/brain new project my-project
$HERMES_HOME/brain/bin/brain add projects/my-project "auth token expires after 1h, not 24h as docs say ⇒ src/auth.py:42"
$HERMES_HOME/brain/bin/brain search "auth token"
$HERMES_HOME/brain/bin/brain review     # interactively triage the inbox
```

Or just tell the agent "remember that X" during a session — it's instructed
(via your SOUL.md / project docs) to use `brain add`/`brain inbox` itself for
durable, project-scoped facts.

## What this is NOT

This is not a replacement for Hermes's built-in `memory` tool (short,
cross-session facts about you, injected every turn) or `skills` (reusable
procedures). Brain is specifically for **durable facts about a specific
project or domain** — the kind of thing you'd otherwise re-discover by
re-reading code or re-running the same investigation every few weeks.

## License

MIT.
