# Upgrading Pomodoro Menu Bar App

As we constantly improve Pomodoro Menu Bar App, you may want to update to the latest version to get new features and bug fixes. 

Since you installed the application by cloning the repository, updating is a straightforward process using Git.

## 🔄 Standard Update Process

Follow these steps to safely update your app to the latest version without losing your tasks or session logs.

### 1. Quit the Application
If the Pomodoro Menu Bar App is currently running, click on the **tomato icon (🍅)** in your macOS menu bar and select **"Quit"** at the very bottom of the menu.

### 2. Pull the Latest Code
Open your **Terminal** application and navigate to the directory where you originally installed the app. By default, this is likely `pomodoro_menubar` (or `pomodoro_menubar`).

```bash
# Navigate to the app directory (adjust the path if necessary)
cd ~/pomodoro_menubar

# Pull the latest changes from the official repository
git pull origin main
```

### 3. Update Dependencies (If Applicable)
Sometimes, an update might include new Python libraries. It is best practice to always update your dependencies after pulling new code.

```bash
# Activate your virtual environment
source venv/bin/activate

# Install any new dependencies
pip install -r requirements.txt
```

### 4. Restart the Application
Now that your code and dependencies are up to date, you can start the application again.

```bash
# Run the application
./manual.sh
```
*(Alternatively, you can just run `./main.py` if your permissions are already set).*

---

## 🚀 Upgrading with LaunchAgent (Auto-start)

If you configured the app to start automatically on login using `launchctl` (LaunchAgent), pulling the code is the same, but you need to restart the background service for the changes to take effect.

1. Open your **Terminal**
2. Run the update commands:
   ```bash
   cd ~/pomodoro_menubar
   git pull origin main
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Restart the LaunchAgent:
   ```bash
   # Unload the old version
   launchctl unload ~/Library/LaunchAgents/com.pomodoro.menubar.plist
   
   # Load the newly updated version
   launchctl load ~/Library/LaunchAgents/com.pomodoro.menubar.plist
   ```

The app will instantly reappear in your menu bar, running the newest version!

---

## 💾 Are My Tasks and Logs Safe?

**Yes!** 
All your user data (tasks, schedules, metadata, and history) is stored locally in `.json` files such as `tasks.json`, `session_logs_history.json`, and the inside the `data/` folder.

Running `git pull` will **never** overwrite these files because they are ignored by the git repository (via `.gitignore`). Your history and planned tasks are perfectly safe during an upgrade. 

If you want to be extra careful, you can back them up first using the custom VPS backup script (`backup_vps.sh`) or manually copying them to another folder.
