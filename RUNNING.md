# Goethe B2 Slot Watcher

Watches one exam page and shouts when booking opens. **It does not book for
you** — you click, in a Chrome window that is already open and already logged in.

## Setup (once)

```bash
uv sync
```

Then open `.env` and set `EXAM_URL` (the page with the `examId` in it) and
`OPEN_TIME` if you know when slots drop.

**Phone alerts (recommended).** Install the [ntfy](https://ntfy.sh) app, subscribe
to a topic name only you would guess (e.g. `goethe-b2-7f3k9x`), and put that same
name in `NTFY_TOPIC`. You'll get a push even if you're away from the desk. Leave it
blank and nothing is ever sent anywhere.

## Running

```bash
uv run watch
```

On a machine with no `.env`, pass everything on the command line instead:

```bash
uv run watch --url "https://www.goethe.de/...?examId=..." --open-time 10:30
```

| Flag | Effect |
|---|---|
| `--url` | Exam URL; skips the prompt |
| `--open-time HH:MM` | When slots drop; skips the prompt |
| `--no-login-wait` | Don't pause for the "press Enter once logged in" step |
| `--keep-browser` | Leave Chrome open after Ctrl+C (default: close it) |

1. It asks for the exam URL and the open time (Enter accepts the `.env` values).
2. Chrome opens on the exam page. **Log in now** — this is the single biggest
   thing you can do to book faster, because it removes the login step from the
   critical path.
3. Press Enter. The watcher reloads the page every 30–60 seconds — but if you
   gave it an `--open-time`, it checks every 3–6 seconds for two minutes either
   side of that minute, then drops back to the slow pace.
4. When the **Select modules** button appears: beeps, a desktop toast, and a
   phone push. Switch to Chrome and book.

**Ctrl+C shuts everything down, Chrome included** — no orphaned chrome.exe
processes left behind. It's wired to SIGINT, SIGTERM and `atexit`, and falls back
to killing the chromedriver service if Chrome has already died. Pass
`--keep-browser` if you'd rather the window survived, which is worth doing if you
might hit Ctrl+C mid-booking.

## Why it's paced this way

An earlier version of this project used Tor, rotating proxies and five parallel
Chrome instances. That's why it kept getting blocked:

- Tor exit nodes are a published list that every anti-bot vendor ingests. Coming
  from Tor is a *worse* signal than your home IP, not a neutral one.
- Five instances hitting the same endpoint in lockstep is itself the giveaway.
  Rotating IPs made it worse — it turned "one person refreshing" into "five
  strangers behaving identically", which is exactly the pattern being scored.

So each layer was raising the score, not lowering it. One honest session at a
human pace doesn't trip either check, and a logged-in browser plus a 30-second
head start is most of the practical advantage anyway — without the risk that a
registration gets cancelled after the fact.

The burst window is rate tuning, not concealment — it's what a person refreshing
at a known release time does, and it's bounded so it can't become hammering. The
error backoff still overrides it: if the site returns a 403 or a high-demand page,
the watcher backs off 120s, doubling to a 900s cap, regardless of burst.

Don't lower `POLL_MIN` / `POLL_MAX` for general watching. A fast rhythm sustained
for hours is the thing that gets a session flagged, and it buys you nothing.

## Files

**On the watcher's run path:**

| File | Role |
|---|---|
| `main.py` | Prompts/flags, launches Chrome, waits for open time, fires the alert |
| `poller.py` | The reload loop, burst window, and backoff when the site pushes back |
| `notifier.py` | Beep + desktop toast + optional ntfy push |
| `config.py` | Selectors, pacing, timeouts (all overridable from `.env`) |

**Kept in the tree, not used by the watcher:**

| File | Role |
|---|---|
| `booker.py` | Click helpers for Select Modules / checkboxes / Continue |
| `instance.py` | Multi-instance worker from the earlier build |
| `tor_manager.py`, `rotating_proxy.py`, `proxy.py` | Tor and proxy plumbing |
| `capture_html.py`, `find_api.py` | Page-capture and endpoint-probing helpers |

These still import and their `.env` keys are still read by `config.py`, but
nothing in the watcher calls them. The previous multi-instance orchestrator
lives in git history — `git checkout HEAD -- main.py` brings it back verbatim.

## Recovered files

`.recovered/instance.uncommitted.pyc` is the compiled bytecode of the
*uncommitted* `instance.py` as it stood on 13 Aug. The committed version of
`instance.py` is what's in the tree; if the uncommitted edits mattered, that
`.pyc` is the only surviving copy and can be decompiled.
