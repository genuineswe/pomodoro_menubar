# Phase 1: Getting Started

## What is Pomodoro Menu Bar App?

Pomodoro Menu Bar App is a **macOS menu bar application** that helps you stay focused using the Pomodoro Technique. Unlike typical timers, this app follows a **fixed daily schedule** that mirrors a professional workday:

- **Morning Block:** 09:00 – 12:00 (6 work sessions)
- **Lunch Break:** 12:00 – 13:00
- **Afternoon Block:** 13:00 – 18:00 (10 work sessions)

> **💡 Customizable:** This schedule is defined in the `SCHEDULE` list at [line 406 of main.py](../main.py#L406). You can modify the times to match your own work hours.

The app automatically transitions between work and break periods, so you never have to manually start or stop a timer during work hours.

## First Launch

After installation (see [README](../readme.md)), you can launch the app in two ways:

### Option A: Direct Run (`./main.py`)

Use this if you've already set up the virtual environment and installed dependencies manually.

```bash
source venv/bin/activate
./main.py
```

**Pros:** Faster startup, no extra checks.  
**Cons:** Assumes everything is already configured.

### Option B: Helper Script (`./manual.sh`)

Use this for a hassle-free experience, especially on first run.

```bash
./manual.sh
```

**What it does:**
1. Checks if a virtual environment (`venv/`) exists – creates one if not.
2. Activates the virtual environment.
3. Installs dependencies (`rumps`, `pyobjc`) if missing.
4. Runs `main.py`.

**Pros:** Handles setup automatically.  
**Cons:** Slightly slower due to checks.

> **Recommendation:** Use `manual.sh` for your first launch, then `./main.py` for subsequent runs.

After launching, look for the **🍅** icon in your macOS menu bar.

## Menu Bar Overview

Click the 🍅 icon to see the main menu:

| Menu Item | Description |
|-----------|-------------|
| **📝 Select Task** | Choose which task you're working on |
| **Task: [name]** | Shows the currently active task |
| **Next: [activity]** | Displays the upcoming session (e.g., "SHORT_BREAK at 09:25") |
| **▶️ Start Pomodoro** | Manually start a session (only visible outside work hours) |
| **⚙️ Manage Tasks** | Add, edit, delete, or complete tasks |
| **📊 Statistics** | View productivity summaries and mood analysis |
| **👋 Quit** | Exit the application |

---

**Next:** [Phase 2: Daily Workflow →](02-daily-workflow.md)
