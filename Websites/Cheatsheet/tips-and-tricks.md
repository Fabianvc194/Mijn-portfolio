# Tips & Tricks — Claude, VS Code & GitHub

Personal reference for getting the most out of my daily tools.

---

## Claude Code

### Essential Commands
| Command | What it does |
|---|---|
| `/model` | Switch between Sonnet, Opus, Haiku |
| `/effort low\|medium\|high\|xhigh` | Set thinking depth |
| `/thinking` | Toggle extended thinking on/off |
| `/compact` | Compress chat history when context gets long |
| `/clear` | Start a fresh session (update CLAUDE.md first!) |
| `/memory` | Scan active rules from CLAUDE.md |
| `/init` | Bootstrap a new project with a base CLAUDE.md |

### Effective Prompting
- Be specific: instead of "fix this", say "fix the error on line 12 in `script.ps1`"
- Use `@filename` to attach a file as context
- Use XML tags to structure complex prompts:
  ```
  <context>I am building a PowerShell backup script</context>
  <code>paste code here</code>
  <question>Why does this fail on line 5?</question>
  ```
- Ask for RCA first: "Explain why this fails before giving the fix"
- Ask for comments: "Add inline comments that explain what each part does"

### When to Use Which Model
| Model | Best for |
|---|---|
| Sonnet 4.6 | Daily coding, scripting, quick questions |
| Opus 4.7 | Complex problems, architecture, deep debugging |
| Haiku 4.5 | Fast, simple lookups |

### Memory Management
- Keep `CLAUDE.md` updated after every important session
- When chat slows down → `/compact` first, then `/clear` if needed
- Always update `CLAUDE.md` before `/clear` — context is lost after

---

## Visual Studio Code

### Essential Shortcuts (Windows)
| Shortcut | Action |
|---|---|
| `Ctrl + P` | Quick open file |
| `Ctrl + Shift + P` | Command palette |
| `Ctrl + `` ` `` | Open terminal |
| `Ctrl + /` | Toggle comment |
| `Alt + Up/Down` | Move line up/down |
| `Ctrl + D` | Select next occurrence |
| `F12` | Go to definition |
| `Shift + F12` | Find all references |
| `Ctrl + Shift + K` | Delete line |

### Useful Extensions for My Stack
- **Python** — Microsoft Python extension (linting, IntelliSense)
- **PowerShell** — Microsoft PowerShell extension
- **Prettier** — Auto-format HTML/CSS/JS
- **GitLens** — See Git blame inline
- **Thunder Client** — Lightweight API tester (no Postman needed)

### Tips
- Use the integrated terminal — keeps everything in one window
- Split editor (`Ctrl + \`) to view CLAUDE.md and your script side by side
- Use workspaces to save your open file layout per project

---

## GitHub

### Daily Git Workflow
```bash
git status                  # Check what changed
git add filename            # Stage specific file (avoid git add -A)
git commit -m "message"     # Commit with clear message
git push                    # Push to remote
```

### Good Commit Message Format
```
Short summary (max 72 chars)

Why this change was made, not what it does.
```

### Useful Commands
| Command | What it does |
|---|---|
| `git log --oneline` | Compact commit history |
| `git diff` | See unstaged changes |
| `git stash` | Temporarily shelve changes |
| `git stash pop` | Restore stashed changes |
| `git checkout -b branchname` | Create and switch to new branch |

### GitHub Tips
- Write meaningful commit messages — future you will thank you
- Use `.gitignore` to keep secrets and temp files out of the repo
- Never commit API keys, passwords, or `.env` files
- Use branches for experiments — keep `main` clean and working

---

## Claude + VS Code + GitHub Together

### Recommended Workflow
1. Open project in VS Code
2. Check `CLAUDE.md` for active rules (`/memory`)
3. Use Claude to write/debug code with `@file` context
4. Test in the VS Code integrated terminal
5. Commit working code with a clear message
6. Push to GitHub

### Power Combos
- **Debug loop:** Paste error in Claude → get RCA + fix → test in VS Code terminal → commit
- **New script:** Use `/init` in Claude → get scaffold → refine in VS Code → push to GitHub
- **Learning mode:** Ask Claude "explain what this does line by line" → add comments → save to repo as reference
- **Context handoff:** Before `/clear`, update `CLAUDE.md` with lessons learned → new session picks up where you left off

---

*Last updated: 2026-04-18*
