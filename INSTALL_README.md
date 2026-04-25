# Installing Claude Code

## Prerequisites

- A **Claude subscription** (Pro, Max, Team, or Enterprise) at [claude.com/pricing](https://claude.com/pricing), OR a **Claude Console** account at [console.anthropic.com](https://console.anthropic.com)
- A terminal or command prompt
- **Windows only:** [Git for Windows](https://git-scm.com/downloads/win) must be installed first

---

## Option 1: CLI (Terminal)

### Native install (recommended — auto-updates in the background)

**macOS / Linux / WSL:**
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Windows PowerShell:**
```powershell
irm https://claude.ai/install.ps1 | iex
```

**Windows CMD:**
```cmd
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

### Homebrew (macOS / Linux)
```bash
brew install --cask claude-code
```
Update manually with `brew upgrade claude-code`.

### WinGet (Windows)
```powershell
winget install Anthropic.ClaudeCode
```
Update manually with `winget upgrade Anthropic.ClaudeCode`.

---

## Option 2: Desktop App

Download for your platform:

| Platform | Link |
|----------|------|
| macOS (Intel & Apple Silicon) | [Download DMG](https://claude.ai/api/desktop/darwin/universal/dmg/latest/redirect) |
| Windows x64 | [Download Setup](https://claude.ai/api/desktop/win32/x64/setup/latest/redirect) |
| Windows ARM64 | [Download Setup](https://claude.ai/api/desktop/win32/arm64/setup/latest/redirect) |

After installing, launch Claude and click the **Code** tab.

---

## First-time setup

1. Open a terminal in your project folder:
   ```bash
   cd /path/to/your/project
   claude
   ```
2. You'll be prompted to **log in** — choose your authentication method (Claude subscription or Console account)
3. Credentials are cached locally; you won't need to log in again

**Verify it works:**
```bash
claude "hello, what can you see in this folder?"
```

---

## Useful commands once running

| Command | What it does |
|---------|-------------|
| `claude` | Start an interactive session |
| `claude "your prompt"` | One-shot command |
| `claude --plan` | Plan mode (no execution) |
| `/help` | Show available commands inside a session |
| `/login` | Switch accounts |
| `/init` | Generate a CLAUDE.md for your project |

---

## Troubleshooting

- Official docs: [code.claude.com/docs/en/quickstart](https://code.claude.com/docs/en/quickstart)
- Troubleshooting guide: [code.claude.com/docs/en/troubleshooting](https://code.claude.com/docs/en/troubleshooting)
