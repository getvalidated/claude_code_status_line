# Claude Code Statusline & Cost Tracker

<img width="100%" alt="screenshot" src="https://github.com/user-attachments/assets/317e225c-1b18-4f57-b359-04be4df44665" />


A custom statusline and session cost tracker for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## What you get

**Statusline** — a rich two-line status bar showing:
- Current directory and git branch with ahead/behind counts
- Model name with fast-mode indicator (↯)
- Context window usage with a color-coded bar (green → yellow → red)
- Session cost and daily running total
- Daily spend visualized as meals (🍗 per $20)

**Cost tracker** — a `SessionEnd` hook that automatically logs every session to a CSV:
- Token breakdown (input, output, cache write, cache read)
- Per-session cost in USD (supports all Claude models + fast mode pricing)
- Session duration, working directory, and model info
- Running total saved to `~/.claude/total_cost.txt`

> [!WARNING]
> This project assumes your terminal font supports **Powerline symbols**.
> Tested and working with [JetBrains Mono](https://www.jetbrains.com/lp/mono/).

## Install

```bash
git clone https://github.com/getvalidated/claude_code_status_line.git
cd claude_code_status_line
bash install.sh
```

Then restart Claude Code.

## One-liner install

```bash
git clone https://github.com/getvalidated/claude_code_status_line.git /tmp/claude_code_status_line && bash /tmp/claude_code_status_line/install.sh
```

## Dependencies

Installed automatically by `install.sh` via `brew` or `apt-get`:
- `jq` — JSON parsing
- `bc` — cost arithmetic
- `git` — branch info

## Files

| File | Installed to | Purpose |
|------|-------------|---------|
| `statusline.sh` | `~/.claude/statusline.sh` | Statusline renderer |
| `hooks/session_cost_tracker.py` | `~/.claude/hooks/session_cost_tracker.py` | Session cost logger |
| `install.sh` | — | Installer script |
