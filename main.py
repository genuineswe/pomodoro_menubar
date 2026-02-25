#!/usr/bin/env python3
"""
Pomodoro Menu Bar App - Menu Bar Application with Task Management
Displays Pomodoro timer in macOS menu bar with comprehensive task tracking
"""

import rumps
import subprocess
from datetime import datetime, timedelta
import time
import os
import webbrowser
import json
import uuid
import threading
import signal
import atexit
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Global reference to app for server callbacks
APP_INSTANCE = None

class TaskServer(BaseHTTPRequestHandler):
    """Simple HTTP server to handle HTML form interactions"""
    
    def do_GET(self):
        """Serve the edit task HTML page"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/edit':
            # Get task ID from query params
            query = parse_qs(parsed_path.query)
            task_id = query.get('id', [None])[0]
            
            if not task_id or not APP_INSTANCE:
                self.send_error(400, "Missing task ID or app instance")
                return
            
            # Find task
            task = None
            for t in APP_INSTANCE.task_manager.tasks:
                if t['id'] == task_id:
                    task = t
                    break
            
            if not task:
                self.send_error(404, "Task not found")
                return
            
            # Read template
            try:
                with open(os.path.join(os.path.dirname(__file__), 'edit_task.html'), 'r') as f:
                    html_content = f.read()
                
                # Inject task data into HTML
                # We'll use simple string replacement for now
                # In a real app, we'd use a template engine
                
                # Prepare data for injection
                repeat_num = str(task.get('repeat_number') or '')
                repeat_unit = task.get('repeat_unit') or ''
                allowed_days = task.get('allowed_days') or []
                
                # Checkboxes for days
                days_js = json.dumps(allowed_days)
                
                html_content = html_content.replace('{{TASK_ID}}', task['id'])
                html_content = html_content.replace('{{TASK_NAME}}', task['name'])
                html_content = html_content.replace('{{TASK_PRIORITY}}', task['priority'])
                html_content = html_content.replace('{{REPEAT_NUMBER}}', repeat_num)
                html_content = html_content.replace('{{REPEAT_UNIT}}', repeat_unit)
                html_content = html_content.replace('{{ALLOWED_DAYS}}', days_js)
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, f"Error serving template: {e}")
                
        elif parsed_path.path == '/add':
            # Serve the add task HTML page
            try:
                with open(os.path.join(os.path.dirname(__file__), 'add.html'), 'r') as f:
                    html_content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, f"Error serving add page: {e}")
                
        elif parsed_path.path == '/paste':
            # Serve the paste task HTML page
            try:
                with open(os.path.join(os.path.dirname(__file__), 'paste_task.html'), 'r') as f:
                    html_content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, f"Error serving paste page: {e}")
        
        elif parsed_path.path == '/settings_page':
            # Serve the settings HTML page
            try:
                with open(os.path.join(os.path.dirname(__file__), 'settings.html'), 'r') as f:
                    html_content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, f"Error serving settings page: {e}")
        
        elif parsed_path.path == '/settings':
            # Return current settings as JSON
            try:
                if APP_INSTANCE:
                    settings = APP_INSTANCE.settings_manager.settings
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(settings).encode('utf-8'))
                else:
                    self.send_error(500, "App instance not available")
            except Exception as e:
                self.send_error(500, f"Error getting settings: {e}")
        
        elif parsed_path.path == '/history':
            # Serve the session history HTML page
            try:
                with open(os.path.join(os.path.dirname(__file__), 'history_today.html'), 'r') as f:
                    html_content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, f"Error serving history page: {e}")
        
        elif parsed_path.path == '/api/sessions/today':
            # Return today's session logs as JSON
            try:
                if APP_INSTANCE:
                    sessions = APP_INSTANCE.session_logger.sessions
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'sessions': sessions}).encode('utf-8'))
                else:
                    self.send_error(500, "App instance not available")
            except Exception as e:
                self.send_error(500, f"Error getting sessions: {e}")
                
        else:
            self.send_error(404, "Not found")


    def _parse_task_data(self, data):
        """Helper to parse and sanitize task data from JSON"""
        name = data.get('name')
        priority = data.get('priority')
        
        # Handle repeat settings
        repeat_number = data.get('repeat_number')
        if repeat_number == "":
            repeat_number = None
        elif repeat_number is not None:
            repeat_number = int(repeat_number)
            
        repeat_unit = data.get('repeat_unit')
        if repeat_unit == "":
            repeat_unit = None
            
        allowed_days = data.get('allowed_days')
        if not allowed_days: # Empty list
            allowed_days = None
            
        return name, priority, repeat_number, repeat_unit, allowed_days

    def _schedule_shutdown(self, delay=1.0):
        """Schedule server shutdown in a separate thread"""
        def shutdown():
            time.sleep(delay)
            if APP_INSTANCE:
                APP_INSTANCE.stop_server()
        
        threading.Thread(target=shutdown, daemon=True).start()

    def do_POST(self):
        """Handle form submission"""
        if self.path == '/create':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                
                if APP_INSTANCE:
                    # Extract data using helper
                    name, priority, repeat_number, repeat_unit, allowed_days = self._parse_task_data(data)
                    
                    # Create task
                    APP_INSTANCE.task_manager.add_task(
                        name=name, 
                        priority=priority,
                        repeat_number=repeat_number,
                        repeat_unit=repeat_unit,
                        allowed_days=allowed_days
                    )
                    
                    # Refresh menu
                    rumps.notification(
                        title="Task Created",
                        subtitle=name,
                        message="Task added successfully via web interface"
                    )
                    APP_INSTANCE.refresh_tasks_submenu()
                    
                    # Schedule server shutdown after 2 seconds
                    self._schedule_shutdown(delay=2.0)
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, f"Error creating task: {e}")
                
        elif self.path == '/create_batch':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                tasks = data.get('tasks', [])
                
                if APP_INSTANCE and tasks:
                    count = 0
                    for task_data in tasks:
                        # Extract data
                        name = task_data.get('name')
                        priority = task_data.get('priority')
                        
                        # Create task
                        APP_INSTANCE.task_manager.add_task(
                            name=name, 
                            priority=priority
                        )
                        count += 1
                    
                    # Refresh menu
                    rumps.notification(
                        title="Batch Tasks Created",
                        subtitle=f"{count} Tasks Added",
                        message="Tasks added successfully via paste"
                    )
                    APP_INSTANCE.refresh_tasks_submenu()
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success', 'count': len(tasks)}).encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, f"Error creating batch tasks: {e}")
        
        elif self.path == '/save_settings':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                
                if APP_INSTANCE:
                    # Update settings
                    APP_INSTANCE.settings_manager.settings = data
                    APP_INSTANCE.settings_manager.save_settings()
                    APP_INSTANCE.refresh_tasks_submenu()
                    
                    rumps.notification(
                        title="Settings Saved",
                        subtitle="Icons Updated",
                        message="Your icon settings have been saved"
                    )
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, f"Error saving settings: {e}")

        elif self.path == '/shutdown':
            # Explicit shutdown request
            if APP_INSTANCE:
                self._schedule_shutdown(delay=0.5)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
            
        elif self.path == '/cancel':
            # Handle cancellation - just shut down server
            if APP_INSTANCE:
                self._schedule_shutdown(delay=1.0)
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                
                if APP_INSTANCE:
                    # Update task
                    task_id = data.get('id')
                    
                    # Extract data using helper
                    name, priority, repeat_number, repeat_unit, allowed_days = self._parse_task_data(data)
                    
                    APP_INSTANCE.task_manager.edit_task(
                        task_id, 
                        name=name, 
                        priority=priority,
                        repeat_number=repeat_number,
                        repeat_unit=repeat_unit,
                        allowed_days=allowed_days
                    )
                    
                    # Refresh menu
                    rumps.notification(
                        title="Task Updated",
                        subtitle=name,
                        message="Changes saved successfully via web editor"
                    )
                    APP_INSTANCE.refresh_tasks_submenu()
                    
                    # Schedule server shutdown after 2 seconds (faster than before)
                    self._schedule_shutdown(delay=2.0)
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, f"Error processing update: {e}")
                
        elif self.path == '/cancel_op': # renamed to avoid conflict if user meant the other cancel
            # Handle cancellation - just shut down server
            if APP_INSTANCE:
                self._schedule_shutdown(delay=1.0)
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'cancelled'}).encode('utf-8'))
            
        else:
            self.send_error(404, "Not found")

    def log_message(self, format, *args):
        return  # Silence server logs

# HARDCODED SCHEDULE (same as pomodoro_timer.py)
class SettingsManager:
    """Manages application settings (icon customization, etc.)"""
    
    DEFAULT_SETTINGS = {
        "icons": {
            "work": "⬆️🔥",
            "short_break": "🚶🚾",
            "long_break": "🥱🥤",
            "lunch": "🍽️"
        }
    }
    
    def __init__(self, settings_file="settings.json"):
        self.settings_file = os.path.join(os.path.dirname(__file__), settings_file)
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from file or create default"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get_icon(self, session_type):
        """Get icon for session type (work, short_break, long_break, lunch)"""
        return self.settings.get("icons", {}).get(session_type, "⏸️")
    
    def set_icon(self, session_type, icon):
        """Set icon for session type"""
        if "icons" not in self.settings:
            self.settings["icons"] = {}
        self.settings["icons"][session_type] = icon
        self.save_settings()


SCHEDULE = [
    # Morning sessions
    {"session": 1, "type": "WORK", "start": "09:00", "end": "09:25"},
    {"session": 1, "type": "SHORT_BREAK", "start": "09:25", "end": "09:30"},
    {"session": 2, "type": "WORK", "start": "09:30", "end": "09:55"},
    {"session": 2, "type": "SHORT_BREAK", "start": "09:55", "end": "10:00"},
    {"session": 3, "type": "WORK", "start": "10:00", "end": "10:25"},
    {"session": 3, "type": "SHORT_BREAK", "start": "10:25", "end": "10:30"},
    {"session": 4, "type": "WORK", "start": "10:30", "end": "10:55"},
    {"session": 4, "type": "LONG_BREAK", "start": "10:55", "end": "11:10"},
    {"session": 5, "type": "WORK", "start": "11:10", "end": "11:35"},
    {"session": 5, "type": "SHORT_BREAK", "start": "11:35", "end": "11:40"},
    {"session": 6, "type": "WORK", "start": "11:40", "end": "12:00"},

    # Lunch
    {"session": "-", "type": "LUNCH", "start": "12:00", "end": "13:00"},

    # Afternoon sessions
    {"session": 1, "type": "WORK", "start": "13:00", "end": "13:25"},
    {"session": 1, "type": "SHORT_BREAK", "start": "13:25", "end": "13:30"},
    {"session": 2, "type": "WORK", "start": "13:30", "end": "13:55"},
    {"session": 2, "type": "SHORT_BREAK", "start": "13:55", "end": "14:00"},
    {"session": 3, "type": "WORK", "start": "14:00", "end": "14:25"},
    {"session": 3, "type": "SHORT_BREAK", "start": "14:25", "end": "14:30"},
    {"session": 4, "type": "WORK", "start": "14:30", "end": "14:55"},
    {"session": 4, "type": "LONG_BREAK", "start": "14:55", "end": "15:10"},
    {"session": 5, "type": "WORK", "start": "15:10", "end": "15:35"},
    {"session": 5, "type": "SHORT_BREAK", "start": "15:35", "end": "15:40"},
    {"session": 6, "type": "WORK", "start": "15:40", "end": "16:05"},
    {"session": 6, "type": "SHORT_BREAK", "start": "16:05", "end": "16:10"},
    {"session": 7, "type": "WORK", "start": "16:10", "end": "16:35"},
    {"session": 7, "type": "SHORT_BREAK", "start": "16:35", "end": "16:40"},
    {"session": 8, "type": "WORK", "start": "16:40", "end": "17:05"},
    {"session": 8, "type": "LONG_BREAK", "start": "17:05", "end": "17:20"},
    {"session": 9, "type": "WORK", "start": "17:20", "end": "17:45"},
    {"session": 9, "type": "SHORT_BREAK", "start": "17:45", "end": "17:50"},
    {"session": 10, "type": "WORK", "start": "17:50", "end": "18:00"}
]

# Dynamic schedule for manual start (generated on-the-fly)
DYNAMIC_SCHEDULE = []
DYNAMIC_SCHEDULE_ACTIVE = False
DYNAMIC_SCHEDULE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "dynamic_schedule.json")

def generate_dynamic_schedule(start_time=None):
    """Generate a dynamic schedule starting from the given time.
    Creates 4 work sessions with breaks, ending with a long break.
    """
    global DYNAMIC_SCHEDULE, DYNAMIC_SCHEDULE_ACTIVE
    
    if start_time is None:
        start_time = datetime.now()
    
    schedule = []
    current_time = start_time
    
    # Generate 4 sessions: work → short break (3x), work → long break (1x)
    for session_num in range(1, 5):
        # Work session (25 minutes)
        work_start = current_time.strftime("%H:%M")
        current_time += timedelta(minutes=25)
        work_end = current_time.strftime("%H:%M")
        
        schedule.append({
            "session": session_num,
            "type": "WORK",
            "start": work_start,
            "end": work_end
        })
        
        # Break
        break_start = current_time.strftime("%H:%M")
        if session_num < 4:
            # Short break (5 minutes)
            current_time += timedelta(minutes=5)
            break_end = current_time.strftime("%H:%M")
            schedule.append({
                "session": session_num,
                "type": "SHORT_BREAK",
                "start": break_start,
                "end": break_end
            })
        else:
            # Long break after 4th session (15 minutes)
            current_time += timedelta(minutes=15)
            break_end = current_time.strftime("%H:%M")
            schedule.append({
                "session": session_num,
                "type": "LONG_BREAK",
                "start": break_start,
                "end": break_end
            })
    
    DYNAMIC_SCHEDULE = schedule
    DYNAMIC_SCHEDULE_ACTIVE = True
    
    # Persist the schedule
    try:
        data_dir = os.path.dirname(DYNAMIC_SCHEDULE_FILE)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        with open(DYNAMIC_SCHEDULE_FILE, 'w') as f:
            json.dump({
                "start_time": start_time.isoformat(),
                "schedule": schedule
            }, f, indent=4)
        print(f"💾 Dynamic schedule saved to {DYNAMIC_SCHEDULE_FILE}")
    except Exception as e:
        print(f"⚠️ Error saving dynamic schedule: {e}")
    
    print(f"📅 Generated dynamic schedule: {len(schedule)} items starting at {start_time.strftime('%H:%M')}")
    for item in schedule:
        print(f"   {item['type']} {item['session']}: {item['start']} - {item['end']}")
    
    return schedule

def clear_dynamic_schedule():
    """Clear the dynamic schedule and revert to fixed schedule"""
    global DYNAMIC_SCHEDULE, DYNAMIC_SCHEDULE_ACTIVE
    DYNAMIC_SCHEDULE = []
    DYNAMIC_SCHEDULE_ACTIVE = False
    
    # Remove persisted file
    try:
        if os.path.exists(DYNAMIC_SCHEDULE_FILE):
            os.remove(DYNAMIC_SCHEDULE_FILE)
            print("🗑️ Dynamic schedule file removed")
    except Exception as e:
        print(f"⚠️ Error removing dynamic schedule file: {e}")
        
    print("📅 Dynamic schedule cleared, reverting to fixed schedule")


class TaskManager:
    """Manages tasks with CRUD operations"""
    
    def __init__(self, tasks_file):
        self.tasks_file = tasks_file
        self.tasks = self.load_tasks()
    
    def load_tasks(self):
        """Load tasks from JSON file"""
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, 'r') as f:
                    data = json.load(f)
                    return data.get('tasks', [])
            except:
                return []
        return []
    
    def save_tasks(self):
        """Save tasks to JSON file"""
        try:
            with open(self.tasks_file, 'w') as f:
                json.dump({'tasks': self.tasks}, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving tasks: {e}")
            return False
    
    def add_task(self, name, priority="Medium", repeat_number=None, repeat_unit=None, allowed_days=None):
        """Add a new task"""
        task = {
            'id': str(uuid.uuid4()),
            'name': name,
            'priority': priority,
            'created_at': datetime.now().isoformat(),
            'status': 'active',
            'repeat_number': repeat_number,
            'repeat_unit': repeat_unit,  # 'day', 'week', 'month'
            'allowed_days': allowed_days,  # List of weekday numbers: 0=Mon, 6=Sun
            'last_completed': None
        }
        self.tasks.append(task)
        self.save_tasks()
        return task
    
    def edit_task(self, task_id, name=None, priority=None, repeat_number=None, repeat_unit=None, allowed_days=None):
        """Edit an existing task"""
        for task in self.tasks:
            if task['id'] == task_id:
                if name:
                    task['name'] = name
                if priority:
                    task['priority'] = priority
                if repeat_number is not None:
                    task['repeat_number'] = repeat_number
                if repeat_unit is not None:
                    task['repeat_unit'] = repeat_unit
                if allowed_days is not None:
                    task['allowed_days'] = allowed_days
                self.save_tasks()
                return True
        return False
    
    def delete_task(self, task_id):
        """Soft delete a task (mark as deleted)"""
        for task in self.tasks:
            if task['id'] == task_id:
                task['status'] = 'deleted'
                self.save_tasks()
                return True
        return False
    
    def hard_delete_task(self, task_id):
        """Permanently delete a task"""
        self.tasks = [t for t in self.tasks if t['id'] != task_id]
        self.save_tasks()
        return True
    
    def get_deleted_tasks(self):
        """Get all deleted tasks"""
        return [t for t in self.tasks if t.get('status') == 'deleted']
    
    def get_task(self, task_id):
        """Get a specific task"""
        for task in self.tasks:
            if task['id'] == task_id:
                return task
        return None
    
    def get_all_active_tasks(self):
        """Get all active tasks"""
        return [t for t in self.tasks if t['status'] == 'active']
    
    def mark_task_completed(self, task_id):
        """Mark task as completed (update last_completed timestamp)"""
        for task in self.tasks:
            if task['id'] == task_id:
                task['last_completed'] = datetime.now().isoformat()
                self.save_tasks()
                return True
        return False
    
    def get_available_tasks(self):
        """Get tasks that are currently available based on repeat schedule and allowed days"""
        active_tasks = self.get_all_active_tasks()
        available = []
        today_weekday = datetime.now().weekday()  # 0=Monday, 6=Sunday
        
        for task in active_tasks:
            # First check if task is allowed on today's weekday
            allowed_days = task.get('allowed_days')
            if allowed_days is not None and len(allowed_days) > 0:
                if today_weekday not in allowed_days:
                    continue  # Skip this task, not allowed today
            
            # Then check repeat schedule
            last_completed = task.get('last_completed')
            repeat_number = task.get('repeat_number')
            repeat_unit = task.get('repeat_unit')
            
            # If never completed, always show
            if last_completed is None:
                available.append(task)
                continue
            
            # If no repeat settings, hide after first completion (one-time task)
            if repeat_number is None or repeat_unit is None:
                continue
            
            # Has repeat settings - check if due
            last_completed_dt = datetime.fromisoformat(last_completed)
            
            # For daily tasks, check if it's a new day (not 24 hours)
            if repeat_unit == 'day' and repeat_number == 1:
                # Daily task should appear only on days AFTER completion day
                # If completed today, should NOT appear
                last_completed_date = last_completed_dt.date()
                today_date = datetime.now().date()
                if today_date > last_completed_date:  # Only show if it's a NEW day
                    available.append(task)
                # If today_date == last_completed_date, skip (already completed today)
            else:
                # For weekly, monthly, or multi-day repeats, use full datetime
                interval_days = {
                    'day': repeat_number,
                    'week': repeat_number * 7,
                    'month': repeat_number * 30,  # approximate
                    'year': repeat_number * 365   # approximate
                }
                
                days = interval_days.get(repeat_unit, 0)
                next_due = last_completed_dt + timedelta(days=days)
                
                if datetime.now() >= next_due:
                    available.append(task)
        
        return available


class SessionLogger:
    """Logs Pomodoro sessions with separated daily and history storage"""
    
    def __init__(self, logs_file_base):
        # logs_file_base is like ".../session_logs.json"
        # We will split it into ".../session_logs_today.json" and ".../session_logs_history.json"
        base, ext = os.path.splitext(logs_file_base)
        self.today_file = f"{base}_today{ext}"
        self.history_file = f"{base}_history{ext}"
        self.legacy_file = logs_file_base # Keep reference for migration
        
        self.sessions = [] # Holds ALL loaded sessions (today + history if loaded)
        self.today_sessions_cache = [] # Only today's sessions
        
        # 1. Automatic Migration Check
        self._check_and_migrate_legacy()
        
        # 2. Archive Check (Move yesterday's `today` to `history`)
        self._archive_old_today_logs()
        
        # 3. Load initial state
        # By default we load ONLY today for performance, history is demand-loaded
        self.load_today_sessions()
    
    def _check_and_migrate_legacy(self):
        """Migrate single session_logs.json to split files if needed"""
        if os.path.exists(self.legacy_file) and not os.path.exists(self.today_file) and not os.path.exists(self.history_file):
            print("📦 Migrating legacy logs to split storage...")
            try:
                with open(self.legacy_file, 'r') as f:
                    data = json.load(f)
                    all_sessions = data.get('sessions', [])
                
                today = datetime.now().date()
                today_sess = []
                history_sess = []
                
                for s in all_sessions:
                    try:
                        s_date = datetime.fromisoformat(s['start_time']).date()
                        if s_date == today:
                            today_sess.append(s)
                        else:
                            history_sess.append(s)
                    except:
                        history_sess.append(s)
                
                # Write to new files
                with open(self.today_file, 'w') as f:
                    json.dump({'sessions': today_sess}, f, indent=2)
                with open(self.history_file, 'w') as f:
                    json.dump({'sessions': history_sess}, f, indent=2)
                    
                # Rename legacy file to avoid confusion/re-migration
                os.rename(self.legacy_file, self.legacy_file + ".migrated")
                print(f"✅ Migration complete: {len(today_sess)} today, {len(history_sess)} history.")
            except Exception as e:
                print(f"❌ Migration failed: {e}")

    def _archive_old_today_logs(self):
        """Move logs from today_file that are not from today into history_file"""
        if not os.path.exists(self.today_file):
            return

        try:
            with open(self.today_file, 'r') as f:
                data = json.load(f)
                current_logs = data.get('sessions', [])
            
            if not current_logs:
                return

            today = datetime.now().date()
            to_keep = []
            to_archive = []
            
            for s in current_logs:
                try:
                    s_date = datetime.fromisoformat(s['start_time']).date()
                    if s_date == today:
                        to_keep.append(s)
                    else:
                        to_archive.append(s)
                except:
                    to_archive.append(s)
            
            if to_archive:
                print(f"🗄️ Archiving {len(to_archive)} logs to history...")
                
                # Append to history
                history_data = {'sessions': []}
                if os.path.exists(self.history_file):
                    try:
                        with open(self.history_file, 'r') as f:
                            history_data = json.load(f)
                    except: pass
                
                history_data['sessions'].extend(to_archive)
                
                with open(self.history_file, 'w') as f:
                    json.dump(history_data, f, indent=2)
                
                # Update today file
                with open(self.today_file, 'w') as f:
                    json.dump({'sessions': to_keep}, f, indent=2)
                
                print("✅ Archiving complete.")
                
        except Exception as e:
            print(f"⚠️ Error archiving logs: {e}")

    def load_today_sessions(self):
        """Load ONLY today's sessions (Fast)"""
        self.today_sessions_cache = []
        if os.path.exists(self.today_file):
            try:
                with open(self.today_file, 'r') as f:
                    data = json.load(f)
                    self.today_sessions_cache = data.get('sessions', [])
            except: pass
        
        # For compatibility with existing code that expects self.sessions
        # We start with only today's sessions. 
        # Tools needing history MUST call load_all_sessions() explicitly.
        self.sessions = self.today_sessions_cache 
        return self.sessions

    def load_all_sessions(self):
        """Load history AND today sessions (Slow) - Call before Analytics"""
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    history = data.get('sessions', [])
            except: pass
            
        # Refresh today just in case
        self.load_today_sessions()
        
        # Combine
        self.sessions = history + self.today_sessions_cache
        return self.sessions

    def load_sessions(self):
        """Compat method - default to loading today only for safety"""
        return self.load_today_sessions()
    
    def save_sessions(self):
        """Save ONLY today's sessions to today_file"""
        try:
            # We assume self.sessions currently contains what fits in 'today' 
            # OR we filter it to be safe.
            # Ideally, we only modify 'today_sessions_cache' and save that.
            
            # Filter to ensure we don't accidentally write history into today file
            # if self.sessions currently holds all data.
            today = datetime.now().date()
            today_only = []
            
            # If self.sessions is huge (history loaded), filtering is safer
            # If self.sessions is small (today only), filtering is fast.
            # However, if we added a new session, it should be in self.sessions.
            
            for s in self.sessions:
                 try:
                    s_date = datetime.fromisoformat(s['start_time']).date()
                    if s_date == today:
                        today_only.append(s)
                 except: pass
            
            with open(self.today_file, 'w') as f:
                json.dump({'sessions': today_only}, f, indent=2)
            
            # Update cache
            self.today_sessions_cache = today_only
            return True
        except Exception as e:
            print(f"Error saving sessions: {e}")
            return False
    
    def log_session(self, session_data):
        """Log a new session"""
        # Skip logging if no task is selected
        if session_data.get('task_id') == 'no-task' or session_data.get('task_name') == '(No Task)':
            print("⏭️ Skipping session log: No task selected")
            return None
        
        session = {
            'id': str(uuid.uuid4()),
            **session_data,
            'logged_at': datetime.now().isoformat()
        }
        
        # Add to memory
        self.sessions.append(session)
        # Add to cache (if separate)
        if session not in self.today_sessions_cache:
            self.today_sessions_cache.append(session)
            
        self.save_sessions()
        return session

    def update_session_feedback(self, session_id, mood=None, reflection=None, blockers=None):
        """Update an existing session with feedback"""
        # We need to find where the session is (Today or History)
        
        updated_in_today = False
        
        # 1. Try updating in Memory (self.sessions)
        for session in self.sessions:
            if session['id'] == session_id:
                if mood is not None: session['mood'] = mood
                if reflection is not None: session['reflection'] = reflection
                if blockers is not None: session['blockers'] = blockers
                
                # Check if this session is in today's cache
                for ts in self.today_sessions_cache:
                    if ts['id'] == session_id:
                         if mood is not None: ts['mood'] = mood
                         if reflection is not None: ts['reflection'] = reflection
                         if blockers is not None: ts['blockers'] = blockers
                         updated_in_today = True
                
        # 2. Save Changes
        if updated_in_today:
             self.save_sessions() # Saves to today_file
             return True
        else:
             # It might be in history file!
             # We only support updating history if we explicitly load & save it.
             # But for simplicity, we can try to patch the history file directly.
             return self._update_history_session(session_id, mood, reflection, blockers)

    def _update_history_session(self, session_id, mood, reflection, blockers):
        """Helper to update a session sitting in history file"""
        if not os.path.exists(self.history_file):
            return False
            
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                history = data.get('sessions', [])
            
            found = False
            for session in history:
                if session['id'] == session_id:
                    if mood is not None: session['mood'] = mood
                    if reflection is not None: session['reflection'] = reflection
                    if blockers is not None: session['blockers'] = blockers
                    found = True
                    break
            
            if found:
                with open(self.history_file, 'w') as f:
                    json.dump({'sessions': history}, f, indent=2)
                return True
        except Exception as e:
            print(f"Error updating history: {e}")
            
        return False

    def get_today_sessions(self):
        """Get today's sessions"""
        # Ensure we return valid today sessions
        # self.sessions usually has today's data, but filtering is safe
        today = datetime.now().date()
        return [s for s in self.sessions 
                if datetime.fromisoformat(s['start_time']).date() == today]
    
    def get_week_sessions(self):
        """Get this week's sessions - REQUIRES FULL HISTORY"""
        # Auto-load history if needed?
        # Better to let Analytics class handle calling load_all_sessions()
        # But if we want it seamless:
        if len(self.sessions) == len(self.today_sessions_cache):
             # Only today loaded, maybe fetch history?
             # For performance, let's assume the caller will call load_all_sessions if they want stats.
             pass
             
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        return [s for s in self.sessions 
                if datetime.fromisoformat(s['start_time']).date() >= week_start]
    
    def get_sessions_by_task(self, task_id):
        """Get sessions for a specific task"""
        return [s for s in self.sessions if s.get('task_id') == task_id]
    
    def calculate_time_per_task(self):
        """Calculate total time spent per task"""
        task_times = {}
        for session in self.sessions:
            task_id = session.get('task_id')
            if task_id:
                duration = session.get('duration_minutes', 0)
                if task_id in task_times:
                    task_times[task_id]['minutes'] += duration
                    task_times[task_id]['seconds'] = task_times[task_id].get('seconds', 0) + int(duration * 60) # Backward compat fallback
                    if 'duration_seconds' in session:
                         task_times[task_id]['seconds'] = task_times[task_id].get('seconds', 0) - int(duration * 60) + session['duration_seconds']

                else:
                    task_times[task_id] = {
                        'task_name': session.get('task_name', 'Unknown'),
                        'priority': session.get('priority', 'Medium'),
                        'minutes': duration,
                        'seconds': session.get('duration_seconds', duration * 60),
                        'sessions': 1
                    }
        return task_times
    
    def get_mood_distribution(self):
        """Get mood distribution from sessions"""
        moods = {}
        for session in self.sessions:
            mood = session.get('mood')
            if mood:
                moods[mood] = moods.get(mood, 0) + 1
        return moods


class Analytics:
    """Generate analytics and reports"""
    
    def __init__(self, session_logger, task_manager):
        self.logger = session_logger
        self.task_manager = task_manager
    
    def generate_daily_summary(self):
        """Generate today's summary"""
        sessions = self.logger.get_today_sessions()
        work_sessions = [s for s in sessions if s.get('session_type') == 'WORK']
        
        total_seconds = sum(s.get('duration_seconds', s.get('duration_minutes', 0) * 60) for s in work_sessions)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        # Get tasks worked on
        task_ids = set(s.get('task_id') for s in work_sessions if s.get('task_id'))
        
        # Find top task
        task_times = {}
        for session in work_sessions:
            tid = session.get('task_id')
            if tid:
                task_times[tid] = task_times.get(tid, 0) + session.get('duration_minutes', 0)
        
        top_task = None
        if task_times:
            top_task_id = max(task_times, key=task_times.get)
            top_task_mins = task_times[top_task_id]
            top_task_obj = self.task_manager.get_task(top_task_id)
            if top_task_obj:
                top_task = f"{top_task_obj['name']} ({top_task_mins // 60}h {top_task_mins % 60}m)"
        
        # Mood summary
        moods = [s.get('mood', '') for s in work_sessions if s.get('mood')]
        mood_str = ''.join(moods) if moods else 'No data'
        
        today_str = datetime.now().strftime("%b %d, %Y")
        
        summary = f"""📊 Today's Summary ({today_str})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Sessions completed: {len(work_sessions)}
⏱️  Total focus time: {hours}h {minutes}m {seconds}s
📝 Tasks worked on: {len(task_ids)}

Top Task: {top_task or 'None'}
Mood: {mood_str}"""
        
        return summary
    
    def generate_weekly_summary(self):
        """Generate this week's summary"""
        sessions = self.logger.get_week_sessions()
        work_sessions = [s for s in sessions if s.get('session_type') == 'WORK']
        
        total_seconds = sum(s.get('duration_seconds', s.get('duration_minutes', 0) * 60) for s in work_sessions)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        # Calculate scheduled sessions (rough estimate: 10 sessions/day * 5 days)
        scheduled = 50
        completion_rate = int((len(work_sessions) / scheduled) * 100) if scheduled > 0 else 0
        
        # Find most productive day
        day_times = {}
        for session in work_sessions:
            day = datetime.fromisoformat(session['start_time']).strftime("%A")
            day_times[day] = day_times.get(day, 0) + session.get('duration_minutes', 0)
        
        most_productive_day = "N/A"
        if day_times:
            top_day = max(day_times, key=day_times.get)
            top_mins = day_times[top_day]
            most_productive_day = f"{top_day} ({top_mins // 60}h {top_mins % 60}m)"
        
        # Top task
        task_times = self.logger.calculate_time_per_task()
        top_task = "None"
        if task_times:
            top_id = max(task_times, key=lambda x: task_times[x]['seconds'])
            top_data = task_times[top_id]
            total_secs = top_data['seconds']
            top_task = f"{top_data['task_name']} ({total_secs // 3600}h {(total_secs % 3600) // 60}m {total_secs % 60}s)"
        
        # Overall mood
        mood_dist = self.logger.get_mood_distribution()
        overall_mood = "😊 Good" if mood_dist else "No data"
        
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%b %d")
        week_end = today.strftime("%b %d, %Y")
        
        summary = f"""📊 This Week ({week_start} - {week_end})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Sessions: {len(work_sessions)} / {scheduled} scheduled
⏱️  Focus time: {hours}h {minutes}m {seconds}s
📈 Completion rate: {completion_rate}%

Most productive day: {most_productive_day}
Top task: {top_task}
Overall mood: {overall_mood}"""
        
        return summary
    
    def get_task_time_breakdown(self):
        """Get time breakdown per task"""
        task_times = self.logger.calculate_time_per_task()
        
        if not task_times:
            return "📊 Time per Task\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nNo tasks tracked yet.\n\nStart tracking time by selecting a task for your work sessions!"
        
        # Sort by time spent (descending)
        sorted_tasks = sorted(task_times.items(), 
                            key=lambda x: x[1]['seconds'], 
                            reverse=True)
        
        total_seconds = sum(data['seconds'] for _, data in sorted_tasks)
        total_sessions = sum(data['sessions'] for _, data in sorted_tasks)
        
        lines = [
            "📊 Time per Task",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Total: {total_seconds // 3600}h {(total_seconds % 3600) // 60}m {total_seconds % 60}s across {total_sessions} sessions\n"
        ]
        
        for task_id, data in sorted_tasks:
            priority_badge = data['priority'][0]  # H, M, L
            name = data['task_name']
            secs = data['seconds']
            hours = secs // 3600
            minutes = (secs % 3600) // 60
            seconds = secs % 60
            sessions = data['sessions']
            percentage = int((secs / total_seconds) * 100) if total_seconds > 0 else 0
            
            bar_length = 20
            filled = int(percentage / 100 * bar_length)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            time_str = f"{hours}h {minutes}m {seconds}s"
            if hours == 0:
                time_str = f"{minutes}m {seconds}s"
            
            lines.append(f"{priority_badge} {name[:20]:<20} {time_str:>10} ({sessions} sess)")
            lines.append(f"   {bar} {percentage}%")
        
        return '\n'.join(lines)
    
    def get_mood_analysis(self):
        """Get mood distribution analysis with insights"""
        mood_dist = self.logger.get_mood_distribution()
        sessions = self.logger.sessions
        
        if not mood_dist:
            return "📊 Mood Analysis\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nNo mood data yet.\n\nMood tracking helps you understand your productivity patterns.\nRate your sessions to see trends!"
        
        total = sum(mood_dist.values())
        
        lines = [
            "📊 Mood Analysis",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Total Sessions Tracked: {total}\n"
        ]
        
        mood_names = {
            '😣': 'Difficult',
            '😊': 'Happy',
            '😢': 'Sad',
            '😎': 'Cool',
            '😁': 'Joyful',
            '💪': 'Productive',
            '😓': 'Struggling',
            '🔥': 'Amazing/On Fire'
        }
        
        # 1. Mood Score Calculation
        # Positive: Happy, Cool, Joyful, Productive, Amazing (1 point)
        # Negative: Difficult, Sad, Struggling (0 points)
        positive_moods = ['😊', '😎', '😁', '💪', '🔥']
        positive_count = sum(mood_dist.get(m, 0) for m in positive_moods)
        mood_score = int((positive_count / total) * 100)
        
        lines.append(f"🌟 Mood Score: {mood_score}/100")
        if mood_score >= 80:
            lines.append("   (You're on fire! 🔥)")
        elif mood_score >= 50:
            lines.append("   (Doing good! 👍)")
        else:
            lines.append("   (Rough patch? Take care! ❤️)")
        lines.append("")
        
        # 2. Distribution
        lines.append("📈 Distribution:")
        for mood, count in sorted(mood_dist.items(), key=lambda x: x[1], reverse=True):
            percentage = int((count / total) * 100)
            name = mood_names.get(mood, 'Unknown')
            bar = '█' * (percentage // 10)  # Compact bar
            lines.append(f"   {mood} {name}: {count} ({percentage}%) {bar}")
            
        # 3. Task Insights
        lines.append("\n💡 Insights:")
        
        # Find best and worst tasks
        task_moods = {} # task -> [mood_scores] (1 for pos, 0 for neg)
        
        for session in sessions:
            if 'mood' in session and session['mood'] and 'task_name' in session:
                mood = session['mood']
                task = session['task_name']
                if task not in task_moods: task_moods[task] = []
                
                if mood in positive_moods:
                    task_moods[task].append(1)
                else:
                    task_moods[task].append(0)
        
        best_task = None
        best_avg = -1
        worst_task = None
        worst_avg = 2
        
        for task, scores in task_moods.items():
            if len(scores) >= 2: # Only consider tasks with at least 2 rated sessions
                avg = sum(scores) / len(scores)
                if avg > best_avg:
                    best_avg = avg
                    best_task = task
                if avg < worst_avg:
                    worst_avg = avg
                    worst_task = task
                    
        if best_task and best_avg >= 0.8:
            lines.append(f"   ✅ You feel best when working on: {best_task}")
        if worst_task and worst_avg <= 0.4:
            lines.append(f"   ⚠️ You struggle most with: {worst_task}")
            
        if not best_task and not worst_task:
             lines.append("   (Track more sessions to see task-specific insights)")

        return '\n'.join(lines)

    def get_mood_analysis_by_period(self, period='daily'):
        """Get mood analysis filtered by period: daily, weekly, or monthly"""
        sessions = self.logger.sessions
        today = datetime.now().date()
        
        # Determine date range based on period
        if period == 'daily':
            start_date = today
            period_label = f"Today ({today.strftime('%d %b %Y')})"
        elif period == 'weekly':
            start_date = today - timedelta(days=6)
            period_label = f"Last 7 Days ({start_date.strftime('%d %b')} - {today.strftime('%d %b')})"
        elif period == 'monthly':
            start_date = today - timedelta(days=29)
            period_label = f"Last 30 Days ({start_date.strftime('%d %b')} - {today.strftime('%d %b')})"
        else:
            start_date = None
            period_label = "All Time"
        
        # Filter sessions by date
        filtered_sessions = []
        for session in sessions:
            if 'start_time' in session:
                try:
                    s_date = datetime.fromisoformat(session['start_time']).date()
                    if start_date is None or s_date >= start_date:
                        filtered_sessions.append(session)
                except:
                    pass
        
        # Calculate mood distribution from filtered sessions
        mood_dist = {}
        for session in filtered_sessions:
            if 'mood' in session and session['mood']:
                mood = session['mood']
                mood_dist[mood] = mood_dist.get(mood, 0) + 1
        
        if not mood_dist:
            return f"📊 Mood Analysis - {period_label}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nNo mood data for this period."
        
        total = sum(mood_dist.values())
        
        lines = [
            f"📊 Mood Analysis - {period_label}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Sessions Tracked: {total}\n"
        ]
        
        mood_names = {
            '😣': 'Difficult',
            '😊': 'Happy',
            '😢': 'Sad',
            '😎': 'Cool',
            '😁': 'Joyful',
            '💪': 'Productive',
            '😓': 'Struggling',
            '🔥': 'Amazing'
        }
        
        # Mood Score
        positive_moods = ['😊', '😎', '😁', '💪', '🔥']
        positive_count = sum(mood_dist.get(m, 0) for m in positive_moods)
        mood_score = int((positive_count / total) * 100)
        
        lines.append(f"🌟 Mood Score: {mood_score}/100")
        if mood_score >= 80:
            lines.append("   (Excellent! 🔥)")
        elif mood_score >= 50:
            lines.append("   (Good! 👍)")
        else:
            lines.append("   (Need improvement ❤️)")
        lines.append("")
        
        # Distribution
        lines.append("📈 Distribution:")
        for mood, count in sorted(mood_dist.items(), key=lambda x: x[1], reverse=True):
            percentage = int((count / total) * 100)
            name = mood_names.get(mood, 'Unknown')
            bar = '█' * (percentage // 10)
            lines.append(f"   {mood} {name}: {count} ({percentage}%) {bar}")

        return '\n'.join(lines)

    def get_task_duration_daily(self):
        """Get task duration breakdown by day (last 7 days)"""
        sessions = self.logger.sessions
        # Group by date -> task
        daily_stats = {}
        
        # Filter for last 7 days
        today = datetime.now().date()
        start_date = today - timedelta(days=6)
        
        for session in sessions:
            try:
                s_date = datetime.fromisoformat(session['start_time']).date()
                if s_date >= start_date:
                    date_str = s_date.strftime("%Y-%m-%d (%a)")
                    if date_str not in daily_stats:
                        daily_stats[date_str] = {}
                    
                    task_name = session.get('task_name', 'Unknown')
                    # Use seconds if available, else minutes * 60
                    seconds = session.get('duration_seconds', session.get('duration_minutes', 0) * 60)
                    
                    daily_stats[date_str][task_name] = daily_stats[date_str].get(task_name, 0) + seconds
            except:
                continue
                
        if not daily_stats:
            return "No data for the last 7 days."
            
        lines = ["📊 Daily Task Duration (Last 7 Days)", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
        
        for date_str in sorted(daily_stats.keys(), reverse=True):
            lines.append(f"\n📅 {date_str}")
            day_total = 0
            for task, seconds in sorted(daily_stats[date_str].items(), key=lambda x: x[1], reverse=True):
                hours = seconds // 3600
                mins = (seconds % 3600) // 60
                secs = seconds % 60
                lines.append(f"  • {task}: {hours}h {mins}m {secs}s")
                day_total += seconds
            
            total_h = day_total // 3600
            total_m = (day_total % 3600) // 60
            total_s = day_total % 60
            lines.append(f"  ∑ Total: {total_h}h {total_m}m {total_s}s")
            
        return '\n'.join(lines)

    def get_task_duration_weekly(self):
        """Get task duration breakdown by week (last 4 weeks)"""
        sessions = self.logger.sessions
        weekly_stats = {}
        
        current_date = datetime.now().date()
        # Start of current week (Monday)
        current_week_start = current_date - timedelta(days=current_date.weekday())
        
        for session in sessions:
            try:
                s_date = datetime.fromisoformat(session['start_time']).date()
                # Calculate week start for this session
                week_start = s_date - timedelta(days=s_date.weekday())
                
                # Only include last 4 weeks
                if week_start >= current_week_start - timedelta(weeks=3):
                    week_str = f"Week of {week_start.strftime('%b %d')}"
                    if week_str not in weekly_stats:
                        weekly_stats[week_str] = {}
                        
                    task_name = session.get('task_name', 'Unknown')
                    seconds = session.get('duration_seconds', session.get('duration_minutes', 0) * 60)
                    weekly_stats[week_str][task_name] = weekly_stats[week_str].get(task_name, 0) + seconds
            except:
                continue
                
        if not weekly_stats:
            return "No data for the last 4 weeks."
            
        lines = ["📊 Weekly Task Duration (Last 4 Weeks)", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
        
        # Sort weeks descending
        sorted_weeks = sorted(weekly_stats.keys(), key=lambda x: datetime.strptime(x.split('Week of ')[1], '%b %d').replace(year=datetime.now().year), reverse=True)
        
        for week in sorted_weeks:
            lines.append(f"\n📅 {week}")
            week_total = 0
            for task, seconds in sorted(weekly_stats[week].items(), key=lambda x: x[1], reverse=True):
                hours = seconds // 3600
                mins = (seconds % 3600) // 60
                secs = seconds % 60
                lines.append(f"  • {task}: {hours}h {mins}m {secs}s")
                week_total += seconds
                
            total_h = week_total // 3600
            total_m = (week_total % 3600) // 60
            total_s = week_total % 60
            lines.append(f"  ∑ Total: {total_h}h {total_m}m {total_s}s")
            
        return '\n'.join(lines)

    def get_task_duration_monthly(self):
        """Get task duration breakdown by month (last 6 months)"""
        sessions = self.logger.sessions
        monthly_stats = {}
        
        today = datetime.now().date()
        six_months_ago = today.replace(day=1) - timedelta(days=30*5) # Approx
        
        for session in sessions:
            try:
                s_date = datetime.fromisoformat(session['start_time']).date()
                if s_date >= six_months_ago.replace(day=1):
                    month_str = s_date.strftime("%B %Y")
                    if month_str not in monthly_stats:
                        monthly_stats[month_str] = {}
                        
                    task_name = session.get('task_name', 'Unknown')
                    seconds = session.get('duration_seconds', session.get('duration_minutes', 0) * 60)
                    monthly_stats[month_str][task_name] = monthly_stats[month_str].get(task_name, 0) + seconds
            except:
                continue
                
        if not monthly_stats:
            return "No data for the last 6 months."
            
        lines = ["📊 Monthly Task Duration (Last 6 Months)", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
        
        # Sort months descending
        def parse_month(m_str):
            return datetime.strptime(m_str, "%B %Y")
            
        for month in sorted(monthly_stats.keys(), key=parse_month, reverse=True):
            lines.append(f"\n📅 {month}")
            month_total = 0
            for task, seconds in sorted(monthly_stats[month].items(), key=lambda x: x[1], reverse=True):
                hours = seconds // 3600
                mins = (seconds % 3600) // 60
                lines.append(f"  • {task}: {hours}h {mins}m")
                month_total += seconds
                
            total_h = month_total // 3600
            total_m = (month_total % 3600) // 60
            lines.append(f"  ∑ Total: {total_h}h {total_m}m")
            
        return '\n'.join(lines)

    def get_today_task_seconds(self):
        """Get dictionary of task_name -> total_seconds for today"""
        sessions = self.logger.sessions
        today_stats = {}
        
        today = datetime.now().date()
        
        for session in sessions:
            try:
                s_date = datetime.fromisoformat(session['start_time']).date()
                if s_date == today:
                    task_name = session.get('task_name', 'Unknown')
                    seconds = session.get('duration_seconds', session.get('duration_minutes', 0) * 60)
                    today_stats[task_name] = today_stats.get(task_name, 0) + seconds
            except:
                continue
        return today_stats


def time_in_range(current, start, end):
    """Check if current time is in range [start, end)"""
    return start <= current < end


def get_current_activity():
    """Get what should be happening right now based on schedule"""
    global DYNAMIC_SCHEDULE_ACTIVE
    
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    current_fixed = None
    current_dynamic = None

    # 1. Check Fixed Schedule first (Weekdays only)
    if now.weekday() < 5:  # Weekday (Mon-Fri)
        for item in SCHEDULE:
            if time_in_range(current_time, item["start"], item["end"]):
                current_fixed = item
                break

    # 2. Check Dynamic Schedule if no active fixed schedule
    if not current_fixed and DYNAMIC_SCHEDULE_ACTIVE and DYNAMIC_SCHEDULE:
        for item in DYNAMIC_SCHEDULE:
            if time_in_range(current_time, item["start"], item["end"]):
                current_dynamic = item
                break

    # 3. Handle schedule conflict
    if current_fixed and current_dynamic:
        # Calculate elapsed time for dynamic session
        dynamic_start = datetime.strptime(current_dynamic["start"], "%H:%M").replace(
            year=now.year, month=now.month, day=now.day)
        elapsed = now - dynamic_start
        elapsed_min = max(0, int(elapsed.total_seconds() // 60))
        
        # Log interrupted dynamic session
        if APP_INSTANCE and APP_INSTANCE.current_task:
            session_data = {
                'task_id': APP_INSTANCE.current_task['id'],
                'task_name': APP_INSTANCE.current_task['name'],
                'priority': APP_INSTANCE.current_task['priority'],
                'session_type': 'WORK',
                'session_number': current_dynamic.get('session', 0),
                'start_time': dynamic_start.isoformat(),
                'end_time': now.isoformat(),
                'duration_minutes': elapsed_min,
                'duration_seconds': int(elapsed.total_seconds()),
                'mood': '',
                'reflection': 'Session interrupted by fixed schedule',
                'blockers': '',
                'completed': False
            }
            APP_INSTANCE.session_logger.log_session(session_data)
        
        # Clear dynamic schedule
        clear_dynamic_schedule()
        return current_fixed

    # 4. Return active schedule based on priority
    return current_fixed or current_dynamic


def send_notification(title, message, sound="Glass"):
    """Send macOS notification"""
    script = f'display notification "{message}" with title "{title}" sound name "{sound}"'
    try:
        subprocess.run(['osascript', '-e', script], timeout=5)
    except:
        pass


def open_break_mode(duration_minutes=5):
    """Open the Zen Mode animation (break.html) with specific duration"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        break_path = os.path.join(current_dir, "break.html")
        
        if os.path.exists(break_path):
            # Create a temporary HTML file with duration embedded
            with open(break_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace the default duration in the HTML - look for the exact line
            content = content.replace(
                "const durationMinutes = parseInt(urlParams.get('duration')) || 5;",
                f'const durationMinutes = {duration_minutes}; // Duration set by Python'
            )
            
            # Write to temp file
            temp_path = os.path.join(current_dir, "break_temp.html")
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Open the temp file
            webbrowser.open(f"file://{temp_path}")
            
            print(f"Opened Zen Mode with duration: {duration_minutes} minutes")
            
            # Schedule cleanup of temp file after 5 minutes
            def cleanup_temp_file():
                time.sleep(300)  # 5 minutes
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        print(f"Cleaned up temp file: {temp_path}")
                except:
                    pass
            
            threading.Thread(target=cleanup_temp_file, daemon=True).start()
            
    except Exception as e:
        print(f"Error opening Zen Mode: {e}")


class SleepWakeObserver:
    """Observer untuk deteksi sleep/wake events dari macOS"""
    
    def __init__(self, callback_obj):
        self.callback_obj = callback_obj
        self._observer_registered = False
    
    def setup(self):
        """Setup sleep/wake observers menggunakan NSWorkspace notification"""
        try:
            import objc
            from AppKit import NSWorkspace, NSObject
            from Foundation import NSNotificationCenter
            
            # Create observer class dinamis dengan objc
            class MacOSObserver(NSObject):
                callback = None
                
                def handleSleep_(self, notification):
                    if self.callback:
                        self.callback.handle_sleep()
                
                def handleWake_(self, notification):
                    if self.callback:
                        self.callback.handle_wake()
                
                def handleScreenLock_(self, notification):
                    if self.callback:
                        self.callback.handle_sleep()
                
                def handleScreenUnlock_(self, notification):
                    if self.callback:
                        self.callback.handle_wake()
            
            # Create instance
            self.observer = MacOSObserver.alloc().init()
            self.observer.callback = self.callback_obj
            
            # Get workspace notification center
            workspace = NSWorkspace.sharedWorkspace()
            nc = workspace.notificationCenter()
            
            # Register for sleep notification
            nc.addObserver_selector_name_object_(
                self.observer,
                'handleSleep:',
                'NSWorkspaceWillSleepNotification',
                None
            )
            
            # Register for wake notification
            nc.addObserver_selector_name_object_(
                self.observer,
                'handleWake:',
                'NSWorkspaceDidWakeNotification',
                None
            )
            
            # Register for screen lock/unlock (distributed notification center)
            from Foundation import NSDistributedNotificationCenter
            dnc = NSDistributedNotificationCenter.defaultCenter()
            
            # Screen lock
            dnc.addObserver_selector_name_object_(
                self.observer,
                'handleScreenLock:',
                'com.apple.screenIsLocked',
                None
            )
            
            # Screen unlock
            dnc.addObserver_selector_name_object_(
                self.observer,
                'handleScreenUnlock:',
                'com.apple.screenIsUnlocked',
                None
            )
            
            self._observer_registered = True
            print("✅ Sleep/wake/lock observers registered successfully")
            
        except Exception as e:
            print(f"⚠️ Could not setup sleep/wake observers: {e}")
            self._observer_registered = False


class PomodoroMenuBarApp(rumps.App):
    def __init__(self):
        super(PomodoroMenuBarApp, self).__init__("🍅", quit_button=None)
        
        # Initialize flag for schedule restore check
        self._schedule_restore_checked = False
        
        # Hide Dock icon (menu bar only app)
        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
            # Get the shared NSApplication instance
            app = NSApplication.sharedApplication()
            # Set activation policy to hide dock icon
            app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception as e:
            print(f"Could not hide Dock icon: {e}")
        
        # Initialize managers
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.task_manager = TaskManager(os.path.join(current_dir, "tasks.json"))
        self.session_logger = SessionLogger(os.path.join(current_dir, "session_logs.json"))
        self.analytics = Analytics(self.session_logger, self.task_manager)
        self.settings_manager = SettingsManager()
        
        self.current_activity = None
        self.break_shown = False
        self.current_task = None
        self.session_start_time = None
        self.pending_feedback_session = None  # Store session data for later feedback
        self.break_start_time = None  # Track when break started
        self.feedback_shown_this_break = False  # Prevent showing feedback multiple times
        self.go_home_shown_today = False  # Track if go home page shown today
        self.task_selection_time = None  # Track when task was selected
        self.next_task = None  # Track task selected during break
        self.urgent_refresh_done = False  # Track if menu was auto-refreshed at 20m mark
        
        # Manual/Classic timer mode state (for off-hours)
        self.manual_running = False
        self.manual_phase = 'idle'  # idle, work, short_break, long_break
        self.manual_session_count = 0  # 0-3, resets after long break
        self.manual_time_remaining = 0  # seconds
        self.manual_start_time = None
        
        # Server configuration (start on-demand)
        global APP_INSTANCE
        APP_INSTANCE = self
        self.server_port = 7878
        self.server_thread = None
        self.httpd = None
        self.last_go_home_date = None  # Track date of last go home page
        self.last_menu_date = datetime.now().date()  # Track date of last menu refresh
        
        # Menu items - Session Info (with no-op callback to appear enabled)
        self.session_info = rumps.MenuItem("Not in session", callback=self.no_op)
        self.task_info = rumps.MenuItem("No task selected", callback=self.no_op)
        self.time_info = rumps.MenuItem("--:--", callback=self.no_op)
        # self.progress_info = rumps.MenuItem("Progress: --", callback=self.no_op)  # Temporarily hidden
        self.next_info = rumps.MenuItem("Next: --", callback=self.no_op)
        
        # Manual timer control
        self.start_stop_item = rumps.MenuItem("▶️ Start Pomodoro", callback=self.toggle_manual_timer)
        
        # Initial menu construction
        select_task_menu = self._build_select_task_menu()
        manage_tasks_menu = self._build_manage_tasks_menu()
        
        # Build menu
        self.menu = [
            select_task_menu,    # Root level Select Task
            None,                # Separator
            # self.session_info,
            self.task_info,
            # self.progress_info,  # Temporarily hidden
            None,  # Separator
            self.next_info,
            None,  # Separator
            self.start_stop_item,  # Manual start/stop
            None,  # Separator
            manage_tasks_menu,   # Root level Manage Tasks
            None,  # Separator
            self._build_statistics_menu(),
            self._build_settings_menu(),
            # None,  # Separator
            # rumps.MenuItem("🧘 Open Zen Mode", callback=self.open_zen),
            None,  # Separator
            rumps.MenuItem("👋 Quit", callback=self.quit_app)
        ]
        
        # Register shutdown handlers to save session on forced termination
        atexit.register(self.save_current_session_on_exit)
        atexit.register(self.cleanup_temp_files)
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        
        # Setup sleep/wake detection
        self._paused_for_sleep = False
        self.sleep_wake_observer = SleepWakeObserver(self)
        self.sleep_wake_observer.setup()

        # Check for previous session (delay slightly to ensure UI is ready)
        # Use a timer that runs only once after 1 second delay
        rumps.Timer(self.check_and_restore_dynamic_schedule, 1).start()
    

    @property
    def is_work_session(self):
        """Check if current active session is WORK type"""
        return self.current_activity and self.current_activity.get('type') == 'WORK'

    def check_and_restore_dynamic_schedule(self, _):
        """Check if there's a valid dynamic schedule to restore - runs only once"""
        # Safety: only run this check once per app instance
        if hasattr(self, '_schedule_restore_checked') and self._schedule_restore_checked:
            return
        self._schedule_restore_checked = True

        try:
            if not os.path.exists(DYNAMIC_SCHEDULE_FILE):
                return
                
            with open(DYNAMIC_SCHEDULE_FILE, 'r') as f:
                data = json.load(f)
                
            schedule = data.get('schedule')
            if not schedule:
                return
                
            # Check validity
            last_item = schedule[-1]
            last_end = last_item['end']
            
            # Since the schedule only stores HH:MM, we assume it's for today or we need to check full datetime
            # The start_time stored in JSON is isoformat, let's use that
            start_time_str = data.get('start_time')
            if not start_time_str:
                clear_dynamic_schedule() # Invalid file
                return
                
            start_time = datetime.fromisoformat(start_time_str)
            now = datetime.now()
            
            # If the schedule started on a different day, it's definitely stale
            if start_time.date() != now.date():
                clear_dynamic_schedule()
                return

            # Check if we passed the end time
            last_end_parts = last_end.split(":")
            last_end_hour = int(last_end_parts[0])
            last_end_min = int(last_end_parts[1])
            
            if now.hour > last_end_hour or (now.hour == last_end_hour and now.minute >= last_end_min):
                clear_dynamic_schedule() # Expired
                return
                
            # It's valid! Ask user
            response = rumps.alert(
                title="Previous Session Found",
                message="A manual Pomodoro session is still active from a previous run. Do you want to resume it?",
                ok="Resume",
                cancel="Start New"
            )
            
            if response == 1: # Resume
                global DYNAMIC_SCHEDULE, DYNAMIC_SCHEDULE_ACTIVE
                DYNAMIC_SCHEDULE = schedule
                DYNAMIC_SCHEDULE_ACTIVE = True
                print("🔄 Dynamic schedule restored from file")
                
                # Update Start/Stop button
                self.start_stop_item.title = "⏹️ Stop Pomodoro"
                self.update_timer(None)
            else:
                clear_dynamic_schedule()
                
        except Exception as e:
            print(f"Error restoring schedule: {str(e)}")
            clear_dynamic_schedule()

    def _handle_signal(self, signum, frame):
        """Handle termination signals"""
        print(f"Received signal {signum}, saving session and exiting...")
        self.save_current_session_on_exit()
        self.cleanup_temp_files()
        # Exit gracefully
        import sys
        sys.exit(0)
    
    def handle_sleep(self):
        """Handle laptop going to sleep or screen lock - log session and pause timer"""
        print("🌙 System going to sleep/lock, saving session...")
        
        # Only log if there's an active work session
        if (self.session_start_time and self.is_work_session):
            
            # Calculate duration
            end_time = datetime.now()
            duration_seconds = int((end_time - self.session_start_time).total_seconds())
            duration_minutes = duration_seconds // 60
            
            # Prepare session data
            task_name = self.current_task['name'] if self.current_task else '(No Task)'
            session_data = {
                'task_id': self.current_task['id'] if self.current_task else 'no-task',
                'task_name': task_name,
                'priority': self.current_task['priority'] if self.current_task else 'None',
                'session_type': 'WORK',
                'session_number': self.current_activity.get('session', 0),
                'start_time': self.session_start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_minutes': duration_minutes,
                'duration_seconds': duration_seconds,
                'mood': '',
                'reflection': 'Session ended due to system sleep/lock',
                'blockers': '',
                'completed': False
            }
            
            # Log it
            self.session_logger.log_session(session_data)
            
            # Set flag so we can resume later if needed
            self._paused_for_sleep = True
            
            # IMPORTANT: Don't clear current_activity or it will look like session ended naturally
            # But we should stop the timer visually or mark it
            rumps.notification("System Sleep", "Pomodoro session paused/logged", f"{duration_minutes}m logged")
            # Clear session start time to indicate no active session
            self.session_start_time = None
            
            # Show notification
            rumps.notification(
                title="⏸️ Session Paused",
                subtitle=f"Logged {duration_minutes}min on {task_name}",
                message="Timer will reset when you return"
            )
            
            print(f"✅ Session logged: {duration_minutes}min (sleep/lock)")
        else:
            print("ℹ️ No active work session to save")
    
    def handle_wake(self):
        """Handle laptop waking up or screen unlock - reset timer to 0"""
        print("☀️ System waking up/unlocking...")
        
        # Check if we were paused due to sleep
        if self._paused_for_sleep:
            # Reset session start time to now (timer starts from 0)
            if self.current_activity and self.current_activity.get('type') == 'WORK':
                self.session_start_time = datetime.now()
                
                # Show notification
                task_name = self.current_task['name'] if self.current_task else 'Unknown'
                rumps.notification(
                    title="▶️ Timer Reset",
                    subtitle=f"Back to {task_name}",
                    message="Timer restarted from 0"
                )
                
                print(f"✅ Timer reset to 0 for task: {task_name}")
            
            self._paused_for_sleep = False
        else:
            print("ℹ️ No sleep-paused session to resume")
    
    def is_within_schedule_hours(self):
        """Check if current time is within schedule hours defined in SCHEDULE"""
        now = datetime.now()
        # Weekend = outside schedule
        if now.weekday() >= 5:
            return False
            
        current_time_str = now.strftime("%H:%M")
        
        # Get dynamic bounds from SCHEDULE
        if not SCHEDULE:
            return False
            
        start_bounds = [item["start"] for item in SCHEDULE]
        end_bounds = [item["end"] for item in SCHEDULE]
        
        return min(start_bounds) <= current_time_str < max(end_bounds)
    
    def toggle_manual_timer(self, _):
        """Start or stop manual Pomodoro timer using dynamic schedule"""
        global DYNAMIC_SCHEDULE_ACTIVE
        
        if self.is_within_schedule_hours():
            # During schedule hours, don't allow manual start
            rumps.notification(
                title="⏰ Schedule Active",
                subtitle="Manual start disabled",
                message="Use schedule during work hours (09:00-18:00)"
            )
            return
        
        if DYNAMIC_SCHEDULE_ACTIVE:
            # Stop timer - clear dynamic schedule
            self.stop_manual_timer()
        else:
            # Start timer - generate dynamic schedule
            self.start_manual_timer()
    
    def start_manual_timer(self):
        """Start manual Pomodoro timer by generating dynamic schedule"""
        # Generate schedule starting from now
        generate_dynamic_schedule(datetime.now())
        
        # Update menu item
        self.start_stop_item.title = "⏹️ Stop Pomodoro"
        
        # Prompt for task selection if no task selected
        if not self.current_task:
            self.prompt_task_selection()
        
        rumps.notification(
            title="▶️ Pomodoro Started",
            subtitle="4 sessions (25min work + break)",
            message="Dynamic schedule generated! 💪"
        )
    
    def stop_manual_timer(self):
        """Stop manual Pomodoro timer by clearing dynamic schedule"""
        # Log current session if in work phase
        activity = get_current_activity()
        if activity and activity.get('type') == 'WORK' and self.session_start_time:
            end_time = datetime.now()
            duration_seconds = int((end_time - self.session_start_time).total_seconds())
            duration_minutes = duration_seconds // 60
            
            if duration_minutes > 0:
                task_name = self.current_task['name'] if self.current_task else '(No Task)'
                session_data = {
                    'task_id': self.current_task['id'] if self.current_task else 'no-task',
                    'task_name': task_name,
                    'priority': self.current_task['priority'] if self.current_task else 'None',
                    'session_type': 'WORK',
                    'session_number': activity.get('session', 0),
                    'start_time': self.session_start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_minutes': duration_minutes,
                    'duration_seconds': duration_seconds,
                    'mood': '',
                    'reflection': 'Manual session stopped early',
                    'blockers': '',
                    'completed': False
                }
                self.session_logger.log_session(session_data)
                print(f"📝 Logged partial session: {duration_minutes}min")
        
        # Clear dynamic schedule and reset state
        clear_dynamic_schedule()
        self.reset_app_state()
        
        # Update menu item
        self.start_stop_item.title = "▶️ Start Pomodoro"
        
        rumps.notification(
            title="⏹️ Pomodoro Stopped",
            subtitle="Dynamic schedule cleared",
            message="Start again when ready"
        )
        print("⏹️ Manual Pomodoro stopped")
    
    def manual_next_phase(self):
        """Transition to next phase in manual Pomodoro cycle"""
        if self.manual_phase == 'work':
            # Log completed work session
            end_time = datetime.now()
            duration_minutes = 25
            duration_seconds = 25 * 60
            
            task_name = self.current_task['name'] if self.current_task else '(No Task)'
            session_data = {
                'task_id': self.current_task['id'] if self.current_task else 'no-task',
                'task_name': task_name,
                'priority': self.current_task['priority'] if self.current_task else 'None',
                'session_type': 'WORK',
                'session_number': self.manual_session_count + 1,
                'start_time': self.manual_start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_minutes': duration_minutes,
                'duration_seconds': duration_seconds,
                'mood': '',
                'reflection': 'Manual Pomodoro session completed',
                'blockers': '',
                'completed': True
            }
            self.session_logger.log_session(session_data)
            print(f"✅ Completed work session {self.manual_session_count + 1}/4")
            
            self.manual_session_count += 1
            
            # Determine break type
            if self.manual_session_count >= 4:
                # Long break after 4 sessions
                self.manual_phase = 'long_break'
                self.manual_time_remaining = 15 * 60  # 15 minutes
                self.manual_session_count = 0  # Reset counter
                
                rumps.notification(
                    title="🎉 Long Break!",
                    subtitle="15 minutes rest",
                    message="Great job completing 4 sessions!"
                )
                # Open Zen Mode
                open_zen_mode(15)
            else:
                # Short break
                self.manual_phase = 'short_break'
                self.manual_time_remaining = 5 * 60  # 5 minutes
                
                rumps.notification(
                    title="☕ Short Break!",
                    subtitle="5 minutes rest",
                    message=f"Session {self.manual_session_count}/4 done"
                )
                # Open Zen Mode
                open_zen_mode(5)
            
            self.manual_start_time = datetime.now()
            
        elif self.manual_phase in ['short_break', 'long_break']:
            # Break ended, start next work session
            self.manual_phase = 'work'
            self.manual_time_remaining = 25 * 60
            self.manual_start_time = datetime.now()
            self.session_start_time = datetime.now()
            
            rumps.notification(
                title="▶️ Back to Work!",
                subtitle="25 minutes focus",
                message=f"Session {self.manual_session_count + 1}/4"
            )
            print(f"🍅 Starting work session {self.manual_session_count + 1}/4")
    
    def update_manual_timer(self):
        """Update manual timer countdown"""
        if not self.manual_running:
            return
        
        self.manual_time_remaining -= 1
        
        if self.manual_time_remaining <= 0:
            # Phase completed, transition
            self.manual_next_phase()
        
        # Update display
        mins = self.manual_time_remaining // 60
        secs = self.manual_time_remaining % 60
        
        # Get phase info
        if self.manual_phase == 'work':
            emoji = self.settings_manager.get_icon('work')
            phase_label = f"Work {self.manual_session_count + 1}/4"
        elif self.manual_phase == 'short_break':
            emoji = self.settings_manager.get_icon('short_break')
            phase_label = "Short Break"
        else:  # long_break
            emoji = self.settings_manager.get_icon('long_break')
            phase_label = "Long Break"
        
        # Update menu bar
        if self.manual_phase == 'work':
            self.title = f"{mins:02d}:{secs:02d}"
        else:
            self.title = f"{emoji} {mins:02d}:{secs:02d}"
        # self.session_info.title = f"🍅 Manual: {phase_label} ({mins:02d}:{secs:02d})"
        # self.time_info.title = ... (Merged into session info)
        
        # Update task display
        if self.current_task:
            time_str = None
            if self.manual_phase == 'work' and self.manual_start_time:
                time_str = self.manual_start_time.strftime("%H:%M:%S")
            self.update_task_display(time_str)
    
    def save_current_session_on_exit(self):
        """Save current work session on exit (called by atexit and signal handlers)"""
        # Avoid duplicate saves
        if not hasattr(self, '_session_saved'):
            self._session_saved = False
        
        if self._session_saved:
            return
        
        # Save current session if there's an active work session
        if hasattr(self, 'session_start_time') and self.session_start_time and \
           hasattr(self, 'current_activity') and self.current_activity and \
           self.current_activity.get('type') == 'WORK':
            
            # Calculate actual duration
            end_time = datetime.now()
            actual_duration_seconds = int((end_time - self.session_start_time).total_seconds())
            actual_duration_minutes = actual_duration_seconds // 60
            
            # Cap duration at 25 minutes
            duration_minutes = min(actual_duration_minutes, 25)
            duration_seconds = min(actual_duration_seconds, 25 * 60)
            
            # Prepare session data
            if hasattr(self, 'current_task') and self.current_task:
                session_data = {
                    'task_id': self.current_task['id'],
                    'task_name': self.current_task['name'],
                    'priority': self.current_task['priority'],
                    'session_type': 'WORK',
                    'session_number': self.current_activity.get('session', 0),
                    'start_time': self.session_start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_minutes': duration_minutes,
                    'duration_seconds': duration_seconds,
                    'mood': '',
                    'reflection': 'Session ended with forced termination',
                    'blockers': '',
                    'completed': True
                }
            else:
                session_data = {
                    'task_id': 'no-task',
                    'task_name': '(No Task Selected)',
                    'priority': 'None',
                    'session_type': 'WORK',
                    'session_number': self.current_activity.get('session', 0),
                    'start_time': self.session_start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_minutes': duration_minutes,
                    'duration_seconds': duration_seconds,
                    'mood': '',
                    'reflection': 'Session ended with forced termination',
                    'blockers': 'No task selected',
                    'completed': True
                }
            
            # Log session
            try:
                if hasattr(self, 'session_logger'):
                    self.session_logger.log_session(session_data)
                    print(f"Session saved: {duration_minutes}min on exit")
                    self._session_saved = True
            except Exception as e:
                print(f"Error saving session on exit: {e}")
    
    def cleanup_temp_files(self):
        """Clean up any temporary HTML files on exit"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            temp_files = ["break_temp.html", "go_home_temp.html"]
            
            for temp_file in temp_files:
                temp_path = os.path.join(current_dir, temp_file)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    print(f"Cleaned up temp file on exit: {temp_path}")
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")

    def reset_app_state(self):
        """Reset all session and task related state variables to initial values"""
        print("🧹 Resetting application state...")
        self.session_start_time = None
        self.current_task = None
        self.task_selection_time = None
        self.next_task = None
        self.break_shown = False
        self.feedback_shown_this_break = False
        self.break_start_time = None
        self._paused_for_sleep = False
        self._task_switched_once = False
        self.pending_feedback_session = None
        
        # Immediate UI Refresh
        self.update_task_display()
        self.update_timer(None)

    def _run_server(self):
        """Run the local HTTP server"""
        try:
            server_address = ('localhost', self.server_port)
            self.httpd = HTTPServer(server_address, TaskServer)
            print(f"Starting local server on port {self.server_port}...")
            self.httpd.serve_forever()
        except Exception as e:
            print(f"Error starting server: {e}")
            self.httpd = None

    def start_server(self):
        """Start the server if not already running"""
        if self.server_thread is None or not self.server_thread.is_alive():
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            # Give server time to start
            time.sleep(0.5)
            print("Server started on-demand")
    
    def stop_server(self):
        """Stop the server gracefully"""
        if self.httpd:
            print("Shutting down server...")
            self.httpd.shutdown()
            self.httpd = None
            self.server_thread = None
            print("Server stopped")

    def set_current_task(self, task):
        """Set the current task from menu selection"""
        # Check if we're in an active work session (uses get_current_activity which handles both scheduled and dynamic)
        activity = get_current_activity()
        is_active_work_session = activity and activity.get('type') == 'WORK'
        
        # If not in active work session, queue the task for next session
        if not is_active_work_session:
            self.next_task = task
            priority_badge = f"[{task['priority'][0]}]"
            self.task_info.title = f"Next: {task['name']} {priority_badge}"
            
            rumps.notification(
                title="Task Queued",
                subtitle=f"Next: {task['name']}",
                message="Will start at next work session"
            )
            return
        
        # If we're switching tasks during an active work session, log the previous task's session first
        if (self.current_task and 
            self.session_start_time and 
            is_active_work_session and
            self.current_task['id'] != task['id']):
            
            # Log the session for the previous task
            end_time = datetime.now()
            actual_duration_seconds = int((end_time - self.session_start_time).total_seconds())
            actual_duration_minutes = actual_duration_seconds // 60
            
            duration_minutes = min(actual_duration_minutes, 25)  # Cap at 25 minutes
            duration_seconds = min(actual_duration_seconds, 25 * 60) # Cap seconds too
            
            if actual_duration_minutes > 30:
                print(f"Warning: Session duration was {actual_duration_minutes}min, capped at 25min. Possible sleep/pause.")
            
            session_data = {
                'task_id': self.current_task['id'],
                'task_name': self.current_task['name'],
                'priority': self.current_task['priority'],
                'session_type': 'WORK',
                'session_number': activity.get('session', 0) if activity else 0,
                'start_time': self.session_start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_minutes': duration_minutes,
                'duration_seconds': duration_seconds,
                'mood': '',  # User can fill later
                'reflection': 'Task switched during session',
                'blockers': '',
                'completed': True
            }
            
            # Log the previous task's session
            self.session_logger.log_session(session_data)
            
            # Refresh tasks menu to update duration stats
            self.refresh_tasks_submenu()
            
            # Reset session start time for the new task
            self.session_start_time = datetime.now()
            
            rumps.notification(
                title="Session Logged",
                subtitle=f"Previous task: {self.current_task['name']}",
                message=f"Logged {duration_minutes}min. Now tracking: {task['name']}"
            )
        
        # Set the new task
        self.current_task = task
        self.task_selection_time = datetime.now()
        
        # If this is the FIRST task selection for the current session (and we are already in session),
        # sync session_start_time to this selection time.
        # This prevents the log from starting at "app start time" or "session boundary time" 
        # when the user actually started the task later (e.g. after resume).
        if is_active_work_session and self.session_start_time and \
           (not hasattr(self, '_task_switched_once') or not self._task_switched_once):
             self.session_start_time = self.task_selection_time
             self._task_switched_once = True
             
        self.update_task_display()
        rumps.notification(
            title="Task Selected",
            subtitle=task['name'],
            message=f"Priority: {task['priority']}"
        )

    # def refresh_tasks_submenu(self):
    #     """Refresh the tasks submenu by rebuilding it and replacing in the main menu"""
    #     try:
    #         # Force reload sessions to ensure latest data
    #         self.session_logger.sessions = self.session_logger.load_sessions()
    #         
    #         tasks = self.task_manager.get_available_tasks()
    #         # Rebuild the tasks menu with current tasks
    #         new_tasks_menu = self._build_tasks_menu(tasks)
    #         
    #         # Construct the full menu list
    #         # We must recreate the list structure as defined in __init__
    #         new_menu = [
    #             # self.session_info,
    #             self.task_info,
    #             self.time_info,
    #             # self.progress_info,  # Temporarily hidden
    #             None,  # Separator
    #             self.next_info,
    #             None,  # Separator
    #             new_tasks_menu,
    #             None,  # Separator
    #             self._build_statistics_menu(),
    #             self._build_settings_menu(),
    #             # None,  # Separator
    #             # rumps.MenuItem("Open Zen Mode", callback=self.open_zen),
    #             None,  # Separator
    #             rumps.MenuItem("Quit", callback=self.quit_app)
    #         ]
    #         
    #         # Clear existing menu to detach items
    #         self.menu.clear()
    #         # Assign new menu
    #         self.menu = new_menu
    #         
    #     except Exception as e:
    #         print(f"Error refreshing tasks menu: {e}")

    def _build_select_task_menu(self, tasks=None):
        """Build the Select Task submenu"""
        if tasks is None:
            tasks = self.task_manager.get_available_tasks()
            
        select_task_menu = rumps.MenuItem("📝 Select Task")
        
        # Populate task items
        if not tasks:
            select_task_menu.add(rumps.MenuItem("No active tasks", callback=None))
        else:
            # 1. Get raw seconds stats efficiently (Single source of truth)
            today_seconds = self.analytics.get_today_task_seconds()
            
            current_activity = get_current_activity()

            # Helper to create callback
            def make_callback(t):
                return lambda sender: self.set_current_task(t)
            
            # Group by priority
            high = [t for t in tasks if t['priority'] == 'High']
            medium = [t for t in tasks if t['priority'] == 'Medium']
            low = [t for t in tasks if t['priority'] == 'Low']
            
            def format_task_label(t):
                # Get raw seconds for this task from session logs only
                total_secs = today_seconds.get(t['name'], 0)

                # Round total seconds to avoid float precision issues in display
                total_secs = round(total_secs, 0)

                # Format duration string manually to avoid extra calls
                h = int(total_secs // 3600)
                m = int((total_secs % 3600) // 60)
                s = int(total_secs % 60)
                
                if h > 0: duration_str = f"{h}h {m}m {s}s"
                elif m > 0: duration_str = f"{m}m {s}s"
                else: duration_str = f"{int(s)}s"
                if total_secs == 0: duration_str = "0m"

                
                # Add repeat info if available
                repeat_num = t.get('repeat_number')
                repeat_unit = t.get('repeat_unit')
                
                if repeat_num and repeat_unit:
                    repeat_str = f" [↻{repeat_num}{repeat_unit[0]}]"  # e.g., [↻1w] for "every 1 week"
                else:
                    repeat_str = " [Once]"  # One-time task
                
                # Add day info if restricted
                allowed_days = t.get('allowed_days')
                if allowed_days:
                    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                    # Check for common patterns
                    if set(allowed_days) == {0, 1, 2, 3, 4}:
                        day_str = " [Weekdays]"
                    elif set(allowed_days) == {5, 6}:
                        day_str = " [Weekend]"
                    else:
                        days = [day_names[d] for d in sorted(allowed_days) if 0 <= d <= 6]
                        day_str = f" [{','.join(days)}]"
                else:
                    day_str = ""
                
                # return f"[{t['priority'][0]}] {t['name']} ({duration_str}){repeat_str}{day_str}"
                return f"{t['name']} ({duration_str})"

            # High
            if high:
                select_task_menu.add(rumps.MenuItem("=== HIGH PRIORITY ===", callback=None))
                for task in high:
                    select_task_menu.add(rumps.MenuItem(format_task_label(task), callback=make_callback(task)))
            
            # Medium
            if medium:
                if select_task_menu.items: select_task_menu.add(rumps.separator)
                select_task_menu.add(rumps.MenuItem("=== MEDIUM PRIORITY ===", callback=None))
                for task in medium:
                    select_task_menu.add(rumps.MenuItem(format_task_label(task), callback=make_callback(task)))
            
            # Low
            if low:
                if select_task_menu.items: select_task_menu.add(rumps.separator)
                select_task_menu.add(rumps.MenuItem("=== LOW PRIORITY ===", callback=None))
                for task in low:
                    select_task_menu.add(rumps.MenuItem(format_task_label(task), callback=make_callback(task)))
                    
        return select_task_menu

    def _build_manage_tasks_menu(self):
        """Build the Manage Tasks submenu"""
        manage_menu = rumps.MenuItem("📋 Manage Tasks")
        
        manage_menu.add(rumps.MenuItem("Add New Task", callback=self.add_task))
        manage_menu.add(rumps.MenuItem("Quick Add (Paste)", callback=self.paste_task))
        manage_menu.add(rumps.separator)
        
        # Get ALL active tasks for Edit/Delete menus
        all_active_tasks = self.task_manager.get_all_active_tasks()
        
        # Build Edit Task submenu
        edit_task_menu = rumps.MenuItem("Edit Task")
        if not all_active_tasks:
            edit_task_menu.add(rumps.MenuItem("No active tasks", callback=None))
        else:
            def make_edit_callback(t):
                return lambda sender: self.edit_task_callback(t)
            # Group by priority for edit
            high = [t for t in all_active_tasks if t['priority'] == 'High']
            medium = [t for t in all_active_tasks if t['priority'] == 'Medium']
            low = [t for t in all_active_tasks if t['priority'] == 'Low']
            if high:
                edit_task_menu.add(rumps.MenuItem("=== HIGH PRIORITY ===", callback=None))
                for task in high:
                    edit_task_menu.add(rumps.MenuItem(task['name'], callback=make_edit_callback(task)))
            if medium:
                if edit_task_menu.items: edit_task_menu.add(rumps.separator)
                edit_task_menu.add(rumps.MenuItem("=== MEDIUM PRIORITY ===", callback=None))
                for task in medium:
                    edit_task_menu.add(rumps.MenuItem(task['name'], callback=make_edit_callback(task)))
            if low:
                if edit_task_menu.items: edit_task_menu.add(rumps.separator)
                edit_task_menu.add(rumps.MenuItem("=== LOW PRIORITY ===", callback=None))
                for task in low:
                    edit_task_menu.add(rumps.MenuItem(task['name'], callback=make_edit_callback(task)))
        manage_menu.add(edit_task_menu)
        
        # Build Delete Task submenu
        delete_task_menu = rumps.MenuItem("Delete Task")
        if not all_active_tasks:
            delete_task_menu.add(rumps.MenuItem("No active tasks", callback=None))
        else:
            def make_delete_callback(t):
                return lambda sender: self.delete_task_callback(t)
            # Group by priority for delete (reuse same grouping)
            high = [t for t in all_active_tasks if t['priority'] == 'High']
            medium = [t for t in all_active_tasks if t['priority'] == 'Medium']
            low = [t for t in all_active_tasks if t['priority'] == 'Low']
            if high:
                delete_task_menu.add(rumps.MenuItem("=== HIGH PRIORITY ===", callback=None))
                for task in high:
                    delete_task_menu.add(rumps.MenuItem(task['name'], callback=make_delete_callback(task)))
            if medium:
                if delete_task_menu.items: delete_task_menu.add(rumps.separator)
                delete_task_menu.add(rumps.MenuItem("=== MEDIUM PRIORITY ===", callback=None))
                for task in medium:
                    delete_task_menu.add(rumps.MenuItem(task['name'], callback=make_delete_callback(task)))
            if low:
                if delete_task_menu.items: delete_task_menu.add(rumps.separator)
                delete_task_menu.add(rumps.MenuItem("=== LOW PRIORITY ===", callback=None))
                for task in low:
                    delete_task_menu.add(rumps.MenuItem(task['name'], callback=make_delete_callback(task)))
        manage_menu.add(delete_task_menu)
        
        # Build Mark Complete submenu (Keep using 'tasks' i.e. available tasks only, or all?)
        # Usually you only mark complete tasks you can do today. So keeping 'tasks' (available) makes sense.
        tasks = self.task_manager.get_available_tasks()
        mark_complete_menu = rumps.MenuItem("Mark Complete for Today")
        if not tasks:
            mark_complete_menu.add(rumps.MenuItem("No active tasks", callback=None))
        else:
            def make_complete_callback(t):
                return lambda sender: self.mark_complete_callback(t)
            # Group by priority
            high = [t for t in tasks if t['priority'] == 'High']
            medium = [t for t in tasks if t['priority'] == 'Medium']
            low = [t for t in tasks if t['priority'] == 'Low']
            if high:
                mark_complete_menu.add(rumps.MenuItem("=== HIGH PRIORITY ===", callback=None))
                for task in high:
                    mark_complete_menu.add(rumps.MenuItem(task['name'], callback=make_complete_callback(task)))
            if medium:
                if mark_complete_menu.items: mark_complete_menu.add(rumps.separator)
                mark_complete_menu.add(rumps.MenuItem("=== MEDIUM PRIORITY ===", callback=None))
                for task in medium:
                    mark_complete_menu.add(rumps.MenuItem(task['name'], callback=make_complete_callback(task)))
            if low:
                if mark_complete_menu.items: mark_complete_menu.add(rumps.separator)
                mark_complete_menu.add(rumps.MenuItem("=== LOW PRIORITY ===", callback=None))
                for task in low:
                    mark_complete_menu.add(rumps.MenuItem(task['name'], callback=make_complete_callback(task)))
        manage_menu.add(mark_complete_menu)
        
        manage_menu.add(rumps.separator)
        manage_menu.add(rumps.MenuItem("View Deleted Tasks", callback=self.view_deleted_tasks))
        
        return manage_menu

    def refresh_tasks_submenu(self):
        """Refresh the tasks submenu by rebuilding it and replacing in the main menu"""
        try:
            # Force reload sessions to ensure latest data
            self.session_logger.sessions = self.session_logger.load_sessions()
            
            tasks = self.task_manager.get_available_tasks()
            
            # Build new menus
            select_task_menu = self._build_select_task_menu(tasks)
            manage_tasks_menu = self._build_manage_tasks_menu()
            
            # Construct the full menu list
            # Construct the full menu list
            new_menu = [
                select_task_menu,    # Root level Select Task
                None,  # Separator
                # self.session_info,
                self.task_info,
                # self.progress_info,  # Temporarily hidden (time_info merged into session_info)
                None,  # Separator
                self.next_info,
                None,  # Separator
                self.start_stop_item,  # Manual start/stop
                None,  # Separator
                manage_tasks_menu,   # Root level Manage Tasks
                None,  # Separator
                self._build_statistics_menu(),
                self._build_settings_menu(),
                # None,  # Separator
                # rumps.MenuItem("🧘 Open Zen Mode", callback=self.open_zen),
                None,  # Separator
                rumps.MenuItem("👋 Quit", callback=self.quit_app)
            ]
            
            # Clear existing menu to detach items
            self.menu.clear()
            # Assign new menu
            self.menu = new_menu
            
        except Exception as e:
            print(f"Error refreshing tasks menu: {e}")

    def _build_statistics_menu(self):
        """Build statistics submenu"""
        stats_menu = rumps.MenuItem("📊 Statistics")
        
        # Summary Submenu
        summary_menu = rumps.MenuItem("Summary")
        summary_menu.add(rumps.MenuItem("Daily Summary", callback=self.show_daily_summary))
        summary_menu.add(rumps.MenuItem("Weekly Summary", callback=self.show_weekly_summary))
        stats_menu.add(summary_menu)
        
        # Task Duration Submenu
        duration_menu = rumps.MenuItem("Task Duration Stats")
        duration_menu.add(rumps.MenuItem("Daily Breakdown", callback=self.show_duration_daily))
        duration_menu.add(rumps.MenuItem("Weekly Breakdown", callback=self.show_duration_weekly))
        duration_menu.add(rumps.MenuItem("Monthly Breakdown", callback=self.show_duration_monthly))
        stats_menu.add(duration_menu)
        
        # Mood Analysis Submenu
        mood_menu = rumps.MenuItem("Mood Analysis")
        mood_menu.add(rumps.MenuItem("📅 Today", callback=self.show_mood_daily))
        mood_menu.add(rumps.MenuItem("📆 This Week", callback=self.show_mood_weekly))
        mood_menu.add(rumps.MenuItem("🗓️ This Month", callback=self.show_mood_monthly))
        mood_menu.add(rumps.separator)
        mood_menu.add(rumps.MenuItem("📊 All Time", callback=self.show_mood_analysis))
        stats_menu.add(mood_menu)
        
        # Add separator and history link
        stats_menu.add(rumps.separator)
        stats_menu.add(rumps.MenuItem("🌐 View Today's History", callback=self.open_history_page))
        
        return stats_menu


    def _build_settings_menu(self):
        """Build Settings menu"""
        settings_menu = rumps.MenuItem("⚙️ Settings")
        
        settings_menu.add(rumps.MenuItem("🌐 Open Settings Page", callback=self.open_settings_page))
        
        return settings_menu
    
    def open_settings_page(self, _):
        """Open settings HTML page in browser"""
        self.start_server()
        webbrowser.open(f"http://localhost:{self.server_port}/settings_page")

    def open_history_page(self, _):
        """Open session history HTML page in browser"""
        self.start_server()
        webbrowser.open(f"http://localhost:{self.server_port}/history")

    # def open_zen(self, _):
    #     """Callback to open Zen Mode with correct duration based on current activity"""
    #     # Force update current activity to be sure
    #     self.current_activity = get_current_activity()
        
    #     duration = 5  # Default
        
    #     print(f"DEBUG: open_zen called. Current activity: {self.current_activity}")
        
    #     if self.current_activity:
    #         type_str = self.current_activity.get('type', '')
    #         if 'LONG' in type_str:
    #             duration = 15
    #         elif type_str == 'LUNCH':
    #             duration = 60
        
    #     print(f"DEBUG: Opening Zen Mode with duration: {duration}")
    #     open_zen_mode(duration)
    
    def open_go_home_page(self):
        """Open GO HOME NOW page at 18:00 with dynamic stats"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        go_home_path = os.path.join(current_dir, "go_home.html")
        
        if os.path.exists(go_home_path):
            try:
                # Calculate today's stats
                sessions = self.session_logger.sessions
                today = datetime.now().date()
                
                today_sessions = []
                for s in sessions:
                    try:
                        if datetime.fromisoformat(s['start_time']).date() == today:
                            # Only count WORK sessions
                            if s.get('session_type') == 'WORK':
                                today_sessions.append(s)
                    except: pass
                    
                # Sort by start time (handling potential missing start_time gracefully)
                today_sessions.sort(key=lambda x: x.get('start_time', ''))

                # Count sessions based on number transitions to handle resets and splits
                session_count = 0
                last_session_num = None
                
                for s in today_sessions:
                    s_num = s.get('session_number')
                    if s_num != last_session_num:
                        session_count += 1
                        last_session_num = s_num
                     
                total_seconds = sum(s.get('duration_seconds', s.get('duration_minutes', 0) * 60) for s in today_sessions)
                total_minutes = total_seconds // 60
                
                # Read template
                with open(go_home_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace placeholders
                content = content.replace('id="sessions-count">-<', f'id="sessions-count">{session_count}<')
                content = content.replace('id="total-minutes">-<', f'id="total-minutes">{total_minutes}<')
                
                # Also disable the fetch logic in the HTML since we are injecting data
                content = content.replace('loadStats();', '// loadStats(); // Disabled by Python injection')
                
                # Write to temp file
                temp_path = os.path.join(current_dir, "go_home_temp.html")
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                webbrowser.open(f"file://{temp_path}")
                
                send_notification(
                    "GO HOME NOW! 🎉",
                    "Time to rest, today's work is finished!",
                    "Glass"
                )
                
                # Schedule cleanup of temp file after 10 minutes
                def cleanup_temp_file():
                    time.sleep(600)  # 10 minutes
                    try:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                            print(f"Cleaned up temp file: {temp_path}")
                    except:
                        pass
                
                threading.Thread(target=cleanup_temp_file, daemon=True).start()
                
            except Exception as e:
                print(f"Error opening/generating go home page: {e}")
                # Fallback to original
                webbrowser.open(f"file://{go_home_path}")
        else:
            print(f"Warning: go_home.html not found at {go_home_path}")
    
    def no_op(self, _):
        """Empty callback for info-only menu items"""
        pass

    def quit_app(self, _):
        """Quit the application"""
        # Save current session using shared method
        self.save_current_session_on_exit()
        self.cleanup_temp_files()
        rumps.quit_application()

    def get_emoji_and_label(self, type_str):
        """Get emoji and label based on activity type (uses custom icons from settings)"""
        if type_str == "WORK":
            return self.settings_manager.get_icon("work"), "WORK"
        elif "LONG" in type_str:
            return self.settings_manager.get_icon("long_break"), "LONG BREAK"
        elif "SHORT" in type_str:
            return self.settings_manager.get_icon("short_break"), "SHORT BREAK"
        elif type_str == "LUNCH":
            return self.settings_manager.get_icon("lunch"), "LUNCH"
        else:
            return "⏸️", "IDLE"

    def create_progress_bar(self, percentage, width=10):
        """Create visual progress bar with colored emoji blocks"""
        filled = int(width * percentage / 100)
        empty = width - filled
        # Use colored emoji blocks for better visual distinction
        # 🟦 = filled (blue), ⬜ = empty (light gray)
        return "🟦" * filled + "⬜" * empty

    def find_next_activity(self):
        """Find the next scheduled activity"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # Check dynamic schedule first if active
        if DYNAMIC_SCHEDULE_ACTIVE and DYNAMIC_SCHEDULE:
            for item in DYNAMIC_SCHEDULE:
                if item["start"] > current_time:
                    emoji, label = self.get_emoji_and_label(item["type"])
                    return f"{emoji} {label} at {item['start']}"
            # If we're at the end of dynamic schedule
            return "Dynamic session ending..."
        
        # Check fixed schedule
        for item in SCHEDULE:
            if item["start"] > current_time:
                # period = "Morning" if item["start"] < "12:00" else ("Lunch" if item["type"] == "LUNCH" else "Afternoon")
                emoji, label = self.get_emoji_and_label(item["type"])
                return f"{emoji} {label} at {item['start']}"
        
        return "No more sessions today"

    # Task Management Callbacks
    # Removed select_task and show_task_selection_alert as they are replaced by dropdown menu

    def add_task(self, _):
        """Add a new task via web interface"""
        # Start server on-demand
        self.start_server()
        
        # Open the HTML editor in default browser
        url = f"http://localhost:{self.server_port}/add"
        webbrowser.open(url)
        
        # Show notification
        rumps.notification(
            title="Opening Task Creator",
            subtitle="New Task",
            message="Please create the task in the browser window that just opened."
        )

    def paste_task(self, _):
        """Quick add tasks via paste interface"""
        # Start server on-demand
        self.start_server()
        
        # Open the paste task HTML page in default browser
        url = f"http://localhost:{self.server_port}/paste"
        webbrowser.open(url)
        
        # Show notification
        rumps.notification(
            title="Quick Add Tasks",
            subtitle="Paste to Create",
            message="Paste your tasks (one per line) in the browser window that just opened."
        )


    def edit_task_callback(self, task):
        """Edit task callback - opens HTML editor"""
        # Check if task is currently active
        if self.current_task and self.current_task['id'] == task['id']:
            rumps.alert(
                title="Cannot Edit Active Task",
                message=f"Task '{task['name']}' is currently active.\n\n⚠️ Please select another task first before editing."
            )
            return
        
        # Start server on-demand
        self.start_server()
        
        # Open the HTML editor in default browser
        url = f"http://localhost:{self.server_port}/edit?id={task['id']}"
        webbrowser.open(url)
        
        # Show notification
        rumps.notification(
            title="Opening Editor",
            subtitle=task['name'],
            message="Please edit the task in the browser window that just opened."
        )

    def mark_complete_callback(self, task):
        """Mark task as complete for today"""
        # Check if this is a one-time task (no repeat settings)
        is_one_time = task.get('repeat_number') is None or task.get('repeat_unit') is None
        
        # Confirm with user
        if is_one_time:
            message = f"Mark '{task['name']}' as complete?\n\nThis is a one-time task and will be automatically deleted."
        else:
            message = f"Mark '{task['name']}' as complete for today?\n\nThis will hide the task until its next scheduled appearance."
        
        response = rumps.alert(
            title="Mark Task Complete?",
            message=message,
            ok="Yes, Mark Complete",
            cancel="Cancel"
        )
        
        if response == 1:  # User confirmed
            # Check if this task is currently active and in a work session
            activity = get_current_activity()
            is_active_work_session = activity and activity.get('type') == 'WORK'
            
            # If this task is currently active during work session, log the session first
            if (self.current_task and
                self.current_task['id'] == task['id'] and
                self.session_start_time and
                is_active_work_session):
                
                # Log the current session before marking complete
                end_time = datetime.now()
                actual_duration_seconds = int((end_time - self.session_start_time).total_seconds())
                actual_duration_minutes = actual_duration_seconds // 60
                
                duration_minutes = min(actual_duration_minutes, 25)  # Cap at 25 minutes
                duration_seconds = min(actual_duration_seconds, 25 * 60)
                
                session_data = {
                    'task_id': self.current_task['id'],
                    'task_name': self.current_task['name'],
                    'priority': self.current_task['priority'],
                    'session_type': 'WORK',
                    'session_number': activity.get('session', 0),
                    'start_time': self.session_start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_minutes': duration_minutes,
                    'duration_seconds': duration_seconds,
                    'mood': '',
                    'reflection': 'Task marked complete during session',
                    'blockers': '',
                    'completed': True
                }
                
                # Log the session
                self.session_logger.log_session(session_data)
                
                # Clear current task (set to None)
                self.current_task = None
                self.task_selection_time = None
                
                # Reset session start time for new task
                self.session_start_time = datetime.now()
                
                # Update task display immediately
                self.update_task_display()
                
                rumps.notification(
                    title="Session Logged",
                    subtitle=f"Task completed: {task['name']}",
                    message=f"Logged {duration_minutes}min. Task cleared from current session."
                )
            
            # Mark task as completed
            self.task_manager.mark_task_completed(task['id'])
            
            # Auto-delete one-time tasks
            if is_one_time:
                self.task_manager.delete_task(task['id'])
                rumps.notification(
                    title="Task Completed & Deleted",
                    subtitle=task['name'],
                    message="One-time task has been removed."
                )
            else:
                rumps.notification(
                    title="Task Marked Complete",
                    subtitle=task['name'],
                    message="This task will reappear based on its repeat schedule."
                )
            
            self.refresh_tasks_submenu()

    def delete_task_callback(self, task):
        """Delete task callback from dropdown menu (soft delete)"""
        # Check if task is currently active
        if self.current_task and self.current_task['id'] == task['id']:
            rumps.alert(
                title="Cannot Delete Active Task",
                message=f"Task '{task['name']}' is currently active.\n\n⚠️ Please select another task first before deleting."
            )
            return
        
        # Confirmation dialog
        response = rumps.alert(
            title=f"Delete Task: {task['name']}?",
            message="This will mark the task as deleted.\nHistorical session logs will be preserved.\n\nAre you sure you want to delete this task?",
            ok="Delete",
            cancel="Cancel"
        )
        
        if response == 1:  # User clicked Delete
            # Soft delete
            self.task_manager.delete_task(task['id'])
            
            # Show notification
            rumps.notification(
                title="Task Deleted",
                subtitle=task['name'],
                message="Task has been marked as deleted"
            )
            
            # Refresh menu
            self.refresh_tasks_submenu()

    def view_deleted_tasks(self, _):
        """View all deleted tasks with option to hard delete"""
        deleted_tasks = self.task_manager.get_deleted_tasks()
        
        if not deleted_tasks:
            rumps.alert("No Deleted Tasks", "No tasks have been deleted yet.")
            return
        
        # Group deleted tasks by priority
        high_priority = [t for t in deleted_tasks if t['priority'] == 'High']
        medium_priority = [t for t in deleted_tasks if t['priority'] == 'Medium']
        low_priority = [t for t in deleted_tasks if t['priority'] == 'Low']
        
        # Build display list
        task_displays = []
        all_tasks_sorted = []  # To match numbering
        numbered_index = 1
        
        if high_priority:
            task_displays.append("  === HIGH PRIORITY ===")
            for task in high_priority:
                task_displays.append(f"  {numbered_index}. [H] {task['name']}")
                all_tasks_sorted.append(task)
                numbered_index += 1
        
        if medium_priority:
            if task_displays:
                task_displays.append("")
            task_displays.append("  === MEDIUM PRIORITY ===")
            for task in medium_priority:
                task_displays.append(f"  {numbered_index}. [M] {task['name']}")
                all_tasks_sorted.append(task)
                numbered_index += 1
        
        if low_priority:
            if task_displays:
                task_displays.append("")
            task_displays.append("  === LOW PRIORITY ===")
            for task in low_priority:
                task_displays.append(f"  {numbered_index}. [L] {task['name']}")
                all_tasks_sorted.append(task)
                numbered_index += 1
        
        message = "\n".join(task_displays)
        
        # Ask user to select task to hard delete
        window = rumps.Window(
            message=f"Deleted Tasks\n\nEnter task number to PERMANENTLY delete (1-{len(all_tasks_sorted)}), or cancel to close:\n\n{message}\u200E",
            title="Deleted Tasks",
            dimensions=(400, 24)
        )
        
        response = window.run()
        if response.clicked and response.text:
            try:
                task_num = int(response.text)
                if 1 <= task_num <= len(all_tasks_sorted):
                    task_to_delete = all_tasks_sorted[task_num - 1]
                    
                    # Final confirmation for hard delete
                    confirm = rumps.alert(
                        title=f"Permanently Delete: {task_to_delete['name']}?",
                        message="⚠️ WARNING: This will PERMANENTLY remove this task from the system.\n\nSession logs will be preserved, but you won't be able to restore this task.\n\nAre you absolutely sure?",
                        ok="Permanently Delete",
                        cancel="Cancel"
                    )
                    
                    if confirm == 1:  # User confirmed hard delete
                        self.task_manager.hard_delete_task(task_to_delete['id'])
                        rumps.notification(
                            title="Task Permanently Deleted",
                            subtitle=task_to_delete['name'],
                            message="Task has been removed from the system"
                        )
                else:
                    rumps.alert("Invalid Number", f"Please enter a number between 1 and {len(all_tasks_sorted)}")
            except ValueError:
                rumps.alert("Invalid Input", "Please enter a valid number")

    def view_all_tasks(self, _):
        """View all tasks grouped by priority"""
        tasks = self.task_manager.get_all_active_tasks()
        
        if not tasks:
            rumps.alert("No Tasks", "You don't have any tasks yet!\n\nCreate one using 'Add New Task'.")
            return
        
        # Group tasks by priority
        high_priority = [t for t in tasks if t['priority'] == 'High']
        medium_priority = [t for t in tasks if t['priority'] == 'Medium']
        low_priority = [t for t in tasks if t['priority'] == 'Low']
        
        # Build task list display grouped by priority with left padding
        task_list = []
        numbered_index = 1
        
        if high_priority:
            task_list.append("  === HIGH PRIORITY ===")  # Left padding
            for task in high_priority:
                task_list.append(f"  {numbered_index}. [H] {task['name']}")  # Left padding
                numbered_index += 1
        
        if medium_priority:
            if task_list:  # Add blank line between sections
                task_list.append("")
            task_list.append("  === MEDIUM PRIORITY ===")  # Left padding
            for task in medium_priority:
                task_list.append(f"  {numbered_index}. [M] {task['name']}")  # Left padding
                numbered_index += 1
        
        if low_priority:
            if task_list:  # Add blank line between sections
                task_list.append("")
            task_list.append("  === LOW PRIORITY ===")  # Left padding
            for task in low_priority:
                task_list.append(f"  {numbered_index}. [L] {task['name']}")  # Left padding
                numbered_index += 1
        
        # Join with newlines for clean left-aligned text
        message = "\n".join(task_list)
        # Add LTR mark for left alignment
        rumps.alert(title="All Tasks", message=message + "\u200E")

    # Statistics Callbacks
    def show_daily_summary(self, _):
        """Show today's summary"""
        summary = self.analytics.generate_daily_summary()
        rumps.alert(title="Daily Summary", message=summary)

    def show_weekly_summary(self, _):
        """Show weekly summary"""
        summary = self.analytics.generate_weekly_summary()
        rumps.alert(title="Weekly Summary", message=summary)



    def show_mood_daily(self, _):
        """Show daily mood analysis"""
        analysis = self.analytics.get_mood_analysis_by_period('daily')
        rumps.alert(title="Mood Analysis - Today", message=analysis)

    def show_mood_weekly(self, _):
        """Show weekly mood analysis"""
        analysis = self.analytics.get_mood_analysis_by_period('weekly')
        rumps.alert(title="Mood Analysis - This Week", message=analysis)

    def show_mood_monthly(self, _):
        """Show monthly mood analysis"""
        self.session_logger.load_all_sessions()
        analysis = self.analytics.get_mood_analysis_by_period('monthly')
        rumps.alert(title="Mood Analysis - This Month", message=analysis)

    def show_mood_analysis(self, _):
        """Show all time mood analysis"""
        analysis = self.analytics.get_mood_analysis()
        rumps.alert(title="Mood Analysis - All Time", message=analysis)

    def show_duration_daily(self, _):
        """Show daily task duration"""
        # Daily usually only needs today, but if "Last 7 days" it needs history
        # Let's check Analytics.get_task_duration_daily
        self.session_logger.load_all_sessions() # It needs last 7 days
        stats = self.analytics.get_task_duration_daily()
        rumps.alert(title="Daily Task Duration", message=stats)

    def show_duration_weekly(self, _):
        """Show weekly task duration"""
        self.session_logger.load_all_sessions()
        stats = self.analytics.get_task_duration_weekly()
        rumps.alert(title="Weekly Task Duration", message=stats)

    def show_duration_monthly(self, _):
        """Show monthly task duration"""
        self.session_logger.load_all_sessions()
        stats = self.analytics.get_task_duration_monthly()
        rumps.alert(title="Monthly Task Duration", message=stats)

    def update_task_display(self, time_str=None):
        """Update task info in menu: Show current task during Work, queued task during Break/Idle"""
        
        # Get current activity to determine if we are in WORK or BREAK
        activity = get_current_activity()
        is_work_session = activity and activity.get('type') == 'WORK'
        
        should_show = False
        
        # 1. During WORK session: Show current task
        if is_work_session:
            if self.current_task:
                priority_badge = f"[{self.current_task['priority'][0]}]"
                title = f"Task: {self.current_task['name']} {priority_badge}"
                
                # Prefer task_selection_time if available
                if self.task_selection_time:
                    time_str = self.task_selection_time.strftime("%H:%M:%S")
                    
                if time_str:
                    title += f" from {time_str}"
                self.task_info.title = title
                should_show = True
            else:
                self.task_info.title = "No task selected"
                should_show = True # Or False if we want to hide it when no task selected in WORK? Prefer showing "No Task" warning.

        # 2. During BREAK/IDLE: Show ONLY if there is a queued 'next_task'
        else:
            if self.next_task:
                priority_badge = f"[{self.next_task['priority'][0]}]"
                self.task_info.title = f"Next: {self.next_task['name']} {priority_badge}"
                should_show = True
            else:
                # Hide to clean up interface during break
                should_show = False
        
        # Apply visibility
        if hasattr(self.task_info, '_menuitem'):
            self.task_info._menuitem.setHidden_(not should_show)

    def prompt_task_selection(self):
        """Prompt user to select a task at start of work session"""
        # If task already selected, don't prompt again
        if self.current_task:
            return
        
        tasks = self.task_manager.get_all_active_tasks()
        
        if not tasks:
            # Use notification instead of blocking alert
            rumps.notification(
                title="No Tasks Available",
                subtitle="Work session started",
                message="Please add a task using 'Manage Tasks > Add New Task'"
            )
            # Try to open add task window automatically? No, might be intrusive.
        else:
            # If still no task after dialog, show reminder
            if not self.current_task:
                rumps.notification(
                    title="No Task Selected",
                    subtitle="Work session started",
                    message="⚠️ Please select a task from '📝 Select Task' menu"
                )

    def prompt_session_feedback(self):
        """Save session immediately and optionally prompt for feedback later (non-blocking)"""
        if not self.session_start_time or not self.current_task:
            return  # No session or no task to log
        
        # Calculate actual duration
        end_time = datetime.now()
        actual_duration_seconds = int((end_time - self.session_start_time).total_seconds())
        actual_duration_minutes = actual_duration_seconds // 60
        
        # Cap duration at 25 minutes to prevent sleep bug
        # If laptop sleeps, duration could be unrealistically long
        duration_minutes = min(actual_duration_minutes, 25)  # Cap at 25 minutes
        duration_seconds = min(actual_duration_seconds, 25 * 60)
        
        # If actual duration is suspiciously long (>30min), log warning
        if actual_duration_minutes > 30:
            print(f"Warning: Session duration was {actual_duration_minutes}min, capped at 25min. Possible sleep/pause.")
        
        # Prepare session data
        if self.current_task:
            # Session with task
            session_data = {
                'task_id': self.current_task['id'],
                'task_name': self.current_task['name'],
                'priority': self.current_task['priority'],
                'session_type': 'WORK',
                'session_number': self.current_activity.get('session', 0) if self.current_activity else 0,
                'start_time': self.session_start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_minutes': duration_minutes,
                'duration_seconds': duration_seconds,
                'mood': '',  # Will be filled later
                'reflection': '',  # Will be filled later
                'blockers': '',  # Will be filled later
                'completed': True
            }
        else:
            # Session without task - still log it!
            session_data = {
                'task_id': 'no-task',
                'task_name': '(No Task Selected)',
                'priority': 'None',
                'session_type': 'WORK',
                'session_number': self.current_activity.get('session', 0) if self.current_activity else 0,
                'start_time': self.session_start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_minutes': duration_minutes,
                'duration_seconds': duration_seconds,
                'mood': '',
                'reflection': '',
                'blockers': 'No task was selected for this session',
                'completed': True
            }
        
        # Log session immediately
        logged_session = self.session_logger.log_session(session_data)
        
        # Refresh tasks menu to update duration stats
        self.refresh_tasks_submenu()
        self.refresh_tasks_submenu()
        
        # Store for potential feedback update later
        task_name = self.current_task['name'] if self.current_task else "(No Task)"
        
        self.pending_feedback_session = {
            'session_id': logged_session['id'],
            'task_name': task_name
        }
        
        # Show simple notification - break can start immediately!
        rumps.notification(
            title="Session Complete!",
            subtitle=f"{duration_minutes}min on {task_name}",
            message="Enjoy your break! ☕"
        )
    
    def prompt_feedback_during_break(self):
        """Show feedback dialogs during break time (optional, non-blocking)"""
        if not self.pending_feedback_session:
            return
        
        task_name = self.pending_feedback_session['task_name']
        
        # Mood tracker
        # Mood tracker using AppleScript for list selection
        try:
            # Updated list with labels
            cmd = """osascript -e 'choose from list {"😊 Happy", "😣 Difficult", "😢 Sad", "😎 Cool", "😁 Joyful", "💪 Productive", "😓 Struggling", "🔥 Amazing"} with title "How was your session?" with prompt "Select your mood:" default items {"😊 Happy"} OK button name "Select" cancel button name "Skip"'"""
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            if not result or result == "false":
                # User cancelled or skipped mood selection
                # We don't set pending_feedback_session to None here, as they might still provide reflection/blockers
                pass
            else:
                # Extract just the emoji (first character) for logging
                mood_emoji = result[0]
                
                self.session_logger.update_session_feedback(
                    self.pending_feedback_session['session_id'],
                    mood=mood_emoji
                )
                
                rumps.notification("Feedback Saved", "Thanks for tracking your mood!", f"You felt: {result}")
                # Don't set pending_feedback_session to None yet, as reflection/blockers are still to come
            
        except Exception as e:
            print(f"Error in mood tracker: {e}")
            # If mood dialog failed, we can still proceed with reflection/blockers
        
        # Reflection (optional)
        reflection_window = rumps.Window(
            message="What did you accomplish? (optional)",
            title="Quick Reflection",
            dimensions=(320, 60)
        )
        reflection_response = reflection_window.run()
        reflection = reflection_response.text if reflection_response.clicked else ""
        
        # Blockers (optional)
        blocker_window = rumps.Window(
            message="Any blockers or issues? (optional)",
            title="Blocker Tracking",
            dimensions=(320, 60)
        )
        blocker_response = blocker_window.run()
        blockers = blocker_response.text if blocker_response.clicked else ""
        
        # Update the logged session with reflection and blockers
        # Note: Mood is already updated above if selected
        self.session_logger.update_session_feedback(
            self.pending_feedback_session['session_id'],
            reflection=reflection,
            blockers=blockers
        )
        
        self.pending_feedback_session = None
        
        # Show confirmation if reflection/blockers provided
        if reflection or blockers:
            rumps.notification(
                title="Feedback Saved",
                subtitle="Session details updated",
                message="Thanks for the feedback!"
            )

    @rumps.timer(1)
    def update_timer(self, _):
        """Update timer every second"""
        
        # Enforce Fixed Schedule Priority:
        # If DYNAMIC_SCHEDULE is active but we are now inside fixed work hours (09:00-18:00 Weekday),
        # automatically kill the dynamic schedule to prevent conflicts.
        if DYNAMIC_SCHEDULE_ACTIVE and self.is_within_schedule_hours():
            print("⚠️ Entering fixed schedule hours - Terminating Dynamic Schedule")
            
            # Log current task before clearing if in WORK session
            if self.current_activity and self.current_activity.get('type') == 'WORK' and self.current_task and self.session_start_time:
                 # Calculate duration until NOW
                 end_time = datetime.now()
                 actual_duration_seconds = int((end_time - self.session_start_time).total_seconds())
                 duration_minutes = min(actual_duration_seconds // 60, 25)
                 duration_seconds = min(actual_duration_seconds, 25 * 60)
                 
                 session_data = {
                    'task_id': self.current_task['id'],
                    'task_name': self.current_task['name'],
                    'priority': self.current_task['priority'],
                    'session_type': 'WORK',
                    'session_number': self.current_activity.get('session', 0),
                    'start_time': self.session_start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_minutes': duration_minutes,
                    'duration_seconds': duration_seconds,
                    'mood': '',
                    'reflection': 'Terminated by Fixed Schedule start',
                    'blockers': '',
                    'completed': True
                }
                 self.session_logger.log_session(session_data)
                 self.refresh_tasks_submenu()
                 
                 rumps.notification(
                    title="Schedule Switched", 
                    subtitle="Entering Fixed Work Hours",
                    message=f"Logged {duration_minutes}m on {self.current_task['name']}"
                 )
            else:
                 rumps.notification("Schedule Switched", "Entering Fixed Work Hours", "Dynamic schedule cleared.")

            clear_dynamic_schedule()
            # Force re-check of activity in next pass
            self.current_activity = None 

        # Show/hide Start Pomodoro button based on schedule hours and dynamic schedule state
        # Uses internal _menuitem (NSMenuItem) to properly hide it
        if hasattr(self.start_stop_item, '_menuitem'):
            should_hide = self.is_within_schedule_hours()
            self.start_stop_item._menuitem.setHidden_(should_hide)
        

        # Update Start/Stop button title based on state
        if DYNAMIC_SCHEDULE_ACTIVE:
            self.start_stop_item.title = "⏹️ Stop Pomodoro"
        else:
            self.start_stop_item.title = "▶️ Start Pomodoro"
        
        now = datetime.now()
        activity = get_current_activity()

        # Check for Dynamic Schedule Completion
        # If schedule is active but no activity is returned, and we are not in fixed hours
        # it means we passed the end of the last dynamic session.
        if DYNAMIC_SCHEDULE_ACTIVE and activity is None and not self.is_within_schedule_hours():
             # Double check we are actually *after* the schedule started (avoid race condition at very start)
             if DYNAMIC_SCHEDULE:
                 last_item = DYNAMIC_SCHEDULE[-1]
                 # Simple specific check: if now > last end
                 current_time_str = now.strftime("%H:%M")
                 if current_time_str >= last_item['end']:
                     print("🏁 Dynamic schedule completed!")
                     clear_dynamic_schedule()
                     self.reset_app_state()
                     
                     rumps.notification(
                        title="All Sessions Completed",
                        subtitle="Great job! 🎉",
                        message="You've finished your manual Pomodoro schedule."
                     )
                     
                     self.start_stop_item.title = "▶️ Start Pomodoro"
                     self.title = "⏸️" # Reset icon immediately
                     # activity is already None, so the display update block below will handle the rest

        # Check for activity change
        if activity != self.current_activity:
            # Session ended - save immediately, don't block for feedback
            if self.current_activity and self.current_activity.get('type') == 'WORK':
                self.prompt_session_feedback()  # Non-blocking now!
            
            self.current_activity = activity
            self.break_shown = False
            self.urgent_refresh_done = False # Reset flag for new session/activity
            
            # New work session started
            if activity and activity.get('type') == 'WORK':
                # CRITICAL FIX: Do not auto-start timer if system is locked/sleeping
                if self._paused_for_sleep:
                     print(f"😴 New session started ({activity.get('session')}) but system is SLEEPING. Timer will remain paused.")
                     self.session_start_time = None # Explicitly ensure no timer is running
                else:
                    self.session_start_time = now
                
                self._task_switched_once = False # Reset flag for new session
                
                # Activate queued task if exists
                if self.next_task:
                    self.current_task = self.next_task
                    self.next_task = None
                    self.task_selection_time = now
                    self.update_task_display()
                    
                    rumps.notification(
                        title="Task Started",
                        subtitle=self.current_task['name'],
                        message="Work session started"
                    )
                self.prompt_task_selection()
                self.feedback_shown_this_break = False  # Reset for next break
            
            # Break started - track start time for feedback timing
            if activity and ('BREAK' in activity.get('type', '') or activity.get('type') == 'LUNCH'):
                self.break_start_time = now
                self.feedback_shown_this_break = False
            
            # Send notification on activity change
            if activity:
                type_str = activity["type"]
                session = activity["session"]
                
                if type_str == "WORK":
                    send_notification("Pomodoro", f"Session {session}: Work time!", "Glass")
                elif "BREAK" in type_str:
                    # Determine duration based on type
                    duration = 15 if "LONG" in type_str else 5
                    
                    send_notification("Break", f"Session {session}: {type_str}", "Crystal")
                    # Open Zen Mode for breaks
                    if not self.break_shown:
                        open_break_mode(duration)
                        self.break_shown = True
                elif type_str == "LUNCH":
                    send_notification("Lunch", "Enjoy your lunch!", "Submarine")
                    # Open Zen Mode for lunch (60 mins)
                    if not self.break_shown:
                        open_break_mode(60)
                        self.break_shown = True
        
        # Show feedback dialog after 1 minute into break (non-blocking)
        if self.current_activity and ('BREAK' in self.current_activity.get('type', '') or self.current_activity.get('type') == 'LUNCH'):
            if self.break_start_time and not self.feedback_shown_this_break:
                elapsed_in_break = (now - self.break_start_time).total_seconds()
                # Show feedback after 60 seconds (1 minute) into break
                if elapsed_in_break >= 60:
                    self.prompt_feedback_during_break()
                    self.feedback_shown_this_break = True
        
        # Check for end of work day - open GO HOME page (dynamic based on SCHEDULE)
        if SCHEDULE:
            last_schedule_end = SCHEDULE[-1]["end"]  # e.g., "21:02"
            end_hour, end_minute = map(int, last_schedule_end.split(":"))
            if now.hour == end_hour and now.minute == end_minute:
                today_date = now.date()
                if self.last_go_home_date != today_date:
                    self.last_go_home_date = today_date
                    self.open_go_home_page()
                    self.reset_app_state()  # Reset state when workday ends
        
        # Check for date change to refresh menu (reset daily stats)
        if self.last_menu_date != now.date():
            self.last_menu_date = now.date()
            
            # Archive yesterday's logs to history
            print("📅 Date changed - Archiving yesterday's logs...")
            self.session_logger._archive_old_today_logs()
            self.session_logger.load_today_sessions()  # Reload to get fresh today data
            
            self.refresh_tasks_submenu()
            self.reset_app_state()  # Reset state on date change (e.g. waking up next morning)
            print(f"Date changed to {self.last_menu_date}, refreshed menu and reset state")

        # Update display
        if activity is None:
            # Weekend or outside work hours
            if now.weekday() >= 5:
                self.title = "🏖️"
            else:
                self.title = "⏸️"
            
            self.time_info.title = "No active session"
            self.next_info.title = f"Next: {self.find_next_activity()}"
            self.task_info.title = "No task selected"
        else:
            # Calculate time
            start_time = datetime.strptime(activity["start"], "%H:%M").time()
            end_time = datetime.strptime(activity["end"], "%H:%M").time()

            start_dt = now.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
            end_dt = now.replace(hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0)

            total_seconds = (end_dt - start_dt).total_seconds()
            elapsed_seconds = (now - start_dt).total_seconds()
            remaining_seconds = (end_dt - now).total_seconds()

            # Ensure values are within bounds
            elapsed_seconds = max(0, min(elapsed_seconds, total_seconds))
            percentage = (elapsed_seconds / total_seconds) * 100 if total_seconds > 0 else 0
            
            # Display time
            mins = int(elapsed_seconds) // 60
            secs = int(elapsed_seconds) % 60

            type_str = activity["type"]
            session = activity["session"]
            emoji, label = self.get_emoji_and_label(type_str)

            # Update menu bar title
            if type_str == "WORK":
                if self.current_task:
                    task_name = self.current_task['name']
                    if len(task_name) > 15:
                        task_name = task_name[:12] + "..."
                    self.title = f"WORK - {task_name} - {activity['end']}"
                else:
                    self.title = f"{mins:02d}:{secs:02d} · 🔘📝"
            else:
                self.title = f"{emoji} · {mins:02d}:{secs:02d}"

            # Update info items
            self.next_info.title = f"Next: {self.find_next_activity()}"
            
            # Update task display
            time_str = None
            if type_str == "WORK" and self.session_start_time:
                time_str = self.session_start_time.strftime("%H:%M:%S")
            self.update_task_display(time_str)


if __name__ == "__main__":
    app = PomodoroMenuBarApp()
    app.run()
