# Pomodoro Menu Bar App

A **macOS menu bar** Pomodoro timer with task management, session logging, web-based task editor, and analytics.

### Why Pomodoro Menu Bar App?
Pomodoro Menu Bar App is built for those who value both their deep work and their peace of mind. It stays quietly in your menu bar, honoring your focus by staying out of the way while gently guiding you through a rhythm of intentional work and necessary rest. It’s not just about getting things done; it’s about ending your day with a sense of clarity, knowing exactly where your energy went.

If this app helps you focus, please support the project: [![GitHub stars](https://img.shields.io/github/stars/gaweki/pomodoro_menubar?style=social)](https://github.com/gaweki/pomodoro_menubar) and share it with a friend. It really helps the project grow!

### Core Benefits:
*   **Stays in your menu bar** – Keeps your workspace clean and minimizes distractions.
*   **Force break with Zen Mode** – A beautiful fullscreen interface that helps you truly disconnect during breaks.
*   **Deep Focus Analytics** – Track exactly where your time goes and monitor your productivity and mood over time.
*   **Autopilot Scheduling** – Automatically follows your scheduled workday without needing to start sessions manually.
*   **Recurring Habit System** – Tasks can repeat daily, weekly, or on specific weekdays to help build long-term routines.
*   **Mood & Reflection Journaling** – Log how you feel and what blocked your progress to improve focus quality.
*   **Smart Task Queueing** – Plan your next move during breaks so you can hit the ground running when the timer starts.
*   **Batch Mode** – Quickly add multiple tasks at once via copy-paste to streamline your planning.
*   **Off-Hours Flexibility** – One-click manual sessions for deep work anytime, even outside your normal schedule.

### 🔽 Quick Download (Recommended)
[Download Latest Release (Source Code .zip)](https://github.com/gaweki/pomodoro_menubar/releases/latest)
*(Note: Requires Python to run)*

## ✨ Features

- **Menu bar timer** showing elapsed time, emoji, priority badge, and progress bar
- **Web-based task management** (add, edit, delete) with modern UI
- **Repeat scheduling** - tasks can repeat daily, weekly, monthly, or yearly with day-of-week filtering
- **Automatic task selection** before each work session
- **Session feedback** (mood, reflection, blockers) during breaks
- **Session logging** to `session_logs.json` with detailed analytics
- **Statistics menu** with daily/weekly summaries, mood analysis, and task duration breakdowns
- **Automated Fixed Schedule** - Morning (09:00-12:00) and Afternoon (13:00-18:00) sessions with predefined work/break cycles.
- **End-of-day page** - automatically opens `go_home.html` at the end of the scheduled workday.
- **Zen Mode** - fullscreen break interface (`break.html`) with calming animations and stress-relief links.
- **Off-Hours Mode** - Dynamic schedule generation for manual work sessions outside 9-5.
- **Smart Sleep Detection** - Automatically saves session and pauses timer when computer sleeps or locks.
- **Auto-Refreshing Menu** - Menu items and durations update in real-time without needing an app restart.
- **Runs as LaunchAgent** - starts automatically on login.

## 🎬 Demo Videos

### 1. Seamless Task Selection
Easily select your next focus directly from the menu bar. If you haven't selected a task, Pomodoro Menu Bar App gently reminds you.
![Task Selection Demo](videos/videofromnotasktoselecttask.gif)

### 2. The Great Transition (Zen Mode)
Watch how Pomodoro Menu Bar App helps you disconnect by automatically opening the Zen Mode fullscreen interface when your session ends.
![Break Transition Demo](videos/videowhilechangeintobreaksession.gif)

### 3. Reflection & Mindfulness
Capture your thoughts and blockers during breaks to maintain high-quality focus throughout the day.
![Reflection Input Demo](videos/videowhileinputreflectiononbreak.gif)
### 4. Flexible Dynamic Scheduling
Need to start working outside your regular hours? Fire up a dynamic session with a single click and let the app handle the rest.
![Dynamic Schedule Demo](videos/videostartpomodoroondynamicschedule.gif)

## 📸 Screenshots

### Menu Bar Interface
![Menu Bar](screenshots/menubar.png)
*The menu bar timer showing active work session with task name and progress*

### Add Task Interface
![Add Task](screenshots/add_task.png)
*Web-based task creation with repeat scheduling and day selection*

### Zen Mode (Break Interface)
![Zen Mode](screenshots/zen_mode.png)
*Fullscreen break interface with calming animations*



## 📦 Installation

### 🚀 Quick Start (Automation)
If you already have Python installed, you can use the included `manual.sh` script which handles setup and dependency installation automatically:
```bash
chmod +x manual.sh
./manual.sh
```

### 1. Prerequisite
Ensure you have Python 3.9+ installed on your macOS.

### 2. Clone the Repository
```bash
git clone https://github.com/gaweki/pomodoro_menubar.git pomodoro_work
cd pomodoro_work
```

### 3. Install Dependencies
```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 4. Run the Application
```bash
# Make executable
chmod +x main.py

# Run
./main.py
```
The timer icon (🍅) should appear in your menu bar.



### 5. Set Up LaunchAgent (Auto-start on Login)

Setting up a LaunchAgent allows the application to run automatically in the background as soon as you log into your Mac.

*   **Why do this?** To ensure your Pomodoro schedule and session tracking are always active without manual intervention. It makes the app truly "set-and-forget."
*   **Who is it for?** Highly recommended for daily users who want the timer to follow their workday schedule automatically.
*   **What happens?** The app will start silently on boot/login, and you'll see the 🍅 icon in your menu bar immediately.

**Option A: Using the provided plist file**
```bash
# Copy the plist to LaunchAgents directory
cp com.pomodoro.menubar.plist ~/Library/LaunchAgents/

# Edit the plist to update paths
nano ~/Library/LaunchAgents/com.pomodoro.menubar.plist

# Load the agent
launchctl load ~/Library/LaunchAgents/com.pomodoro.menubar.plist
```

**Option B: Manual plist creation**

1. Create a file at `~/Library/LaunchAgents/com.pomodoro.menubar.plist`.
2. Replace `YOUR_USERNAME` and `PATH_TO_PROJECT` with your actual Mac username and the folder where you cloned the repo.
3. **Note:** We recommend using the python executable inside your `venv` to ensure dependencies like `rumps` are found.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.pomodoro.menubar</string>
    <key>ProgramArguments</key>
    <array>
        <!-- Path to python inside your virtual environment -->
        <string>/Users/YOUR_USERNAME/PATH_TO_PROJECT/venv/bin/python3</string>
        <!-- Path to your main.py file -->
        <string>/Users/YOUR_USERNAME/PATH_TO_PROJECT/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/PATH_TO_PROJECT</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/tmp/pomodoro_menubar.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/pomodoro_menubar.out</string>
</dict>
</plist>
```

Then load it:
```bash
launchctl load ~/Library/LaunchAgents/com.pomodoro.menubar.plist
```

### Managing the LaunchAgent
```bash
# Stop the agent
launchctl unload ~/Library/LaunchAgents/com.pomodoro.menubar.plist

# Restart the agent
launchctl unload ~/Library/LaunchAgents/com.pomodoro.menubar.plist&&launchctl load ~/Library/LaunchAgents/com.pomodoro.menubar.plist

# Check if running
launchctl list | grep pomodoro
```

## � Fixed Schedule (Mon-Fri)

The application follows a structured workday. It automatically switches activities based on the time:

| Period | Time | Session Numbers | Activity Pattern |
| :--- | :--- | :--- | :--- |
| **Morning** | 09:00 - 12:00 | 1 - 6 | 25m Work / 5m Break (Long break after session 4) |
| **Lunch** | 12:00 - 13:00 | - | 60m Break |
| **Afternoon & Evening** | 13:00 - End | 1 - 15+ | 25m Work / 5m Break (Cycles continue based on `SCHEDULE`) |

*   **Fixed Schedule:** The app follows the `SCHEDULE` list defined in `main.py`.
*   **Off-Hours:** Outside these times (or on weekends), the app defaults to **Manual Mode**.


> **Customizing the Schedule:** You can modify the `SCHEDULE` list at the beginning of `main.py` to match your own work hours and break preferences. Simply update the `start` and `end` times for each session.

## 🛠️ Configuration

## ▶️ Usage

For detailed information on how to configure the application, schedules, and advanced settings, please refer to the [docs](./docs) directory.

## 📂 Project Structure

```
pomodoro_work/
├── main.py                       # Main application
├── add.html                      # Add task web interface
├── edit_task.html                # Edit task web interface
├── break.html                    # Zen Mode break interface
├── go_home.html                  # End-of-day page
├── tasks.json                    # Task storage (auto-generated)
├── session_logs.json             # Session logs (auto-generated)
├── com.pomodoro.menubar.plist  # LaunchAgent config
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🧹 Cleanup

```bash
# Remove LaunchAgent
launchctl unload ~/Library/LaunchAgents/com.pomodoro.menubar.plist
rm ~/Library/LaunchAgents/com.pomodoro.menubar.plist
```

## 🐛 Troubleshooting

### App doesn't start
- Check logs: `tail -f ~/pomodoro_menubar_error.log` (or path defined in your `.plist`)
- Verify Python path in plist matches your system: `which python3`
- Ensure script is executable: `chmod +x main.py`

### Web interface doesn't open
- Check if port 7878 is available: `lsof -i :7878`
- Try changing the port in `main.py`

### Tasks not appearing
- Check `tasks.json` for valid JSON syntax
- Verify task has correct `allowed_days` and `repeat_unit` settings
- Check if task is marked as deleted

## 📜 License

MIT - feel free to fork and improve!
