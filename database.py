import json
import os
import base64
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from config import DATABASE_FILE, ENCRYPTION_KEY, ENABLE_ENCRYPTION, DATABASE_SAVE_DEBOUNCE, MAX_REMINDERS_PER_USER, DEADLINE_REMINDER_HOURS

class TodoDatabase:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.fernet = self._setup_encryption()
        self.data = self._load_data()
        if 'user_mapping' not in self.data:
            self.data['user_mapping'] = {}
        if 'reminders' not in self.data:
            self.data['reminders'] = {}
        
        # Add caching for better performance
        self._cache = {}
        self._last_save = datetime.now()
        self._save_pending = False
    
    def _setup_encryption(self) -> Optional[Fernet]:
        """Set up encryption if enabled"""
        if not ENABLE_ENCRYPTION:
            return None
        
        try:
            # Generate a key from the encryption key using PBKDF2
            salt = b'todo_bot_salt'  # Fixed salt for consistency
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(ENCRYPTION_KEY.encode()))
            return Fernet(key)
        except Exception as e:
            print(f"Warning: Failed to setup encryption: {e}")
            return None
    
    def _hash_user_id(self, user_id: str) -> str:
        """Hash user ID for privacy"""
        secret = ENCRYPTION_KEY.encode()
        return hmac.new(secret, user_id.encode(), hashlib.sha256).hexdigest()
    
    def _hash_task_content(self, task_content: str) -> str:
        """Hash task content for privacy"""
        secret = ENCRYPTION_KEY.encode()
        return hmac.new(secret, task_content.encode(), hashlib.sha256).hexdigest()
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt data if encryption is enabled"""
        if not self.fernet:
            return data
        try:
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            print(f"Warning: Failed to encrypt data: {e}")
            return data
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data if encryption is enabled"""
        if not self.fernet:
            return encrypted_data
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            print(f"Warning: Failed to decrypt data: {e}")
            return encrypted_data
    
    def _load_data(self) -> Dict:
        """Load data from file with decryption"""
        if not os.path.exists(self.db_file):
            return {}
        
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                encrypted_content = f.read()
            
            if encrypted_content.strip():
                decrypted_content = self._decrypt_data(encrypted_content)
                return json.loads(decrypted_content)
            else:
                return {}
        except Exception as e:
            print(f"Warning: Failed to load database: {e}")
            return {}
    
    def _save_data(self, force: bool = False):
        """Save data to file with encryption - optimized with debouncing"""
        now = datetime.now()
        
        # Only save if forced, or if it's been more than the configured debounce time since last save
        if not force and (now - self._last_save).total_seconds() < DATABASE_SAVE_DEBOUNCE:
            self._save_pending = True
            return
        
        try:
            json_content = json.dumps(self.data, indent=2, ensure_ascii=False)
            encrypted_content = self._encrypt_data(json_content)
            
            with open(self.db_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_content)
            
            self._last_save = now
            self._save_pending = False
        except Exception as e:
            print(f"Error saving database: {e}")
    
    def _get_user_tasks(self, hashed_user_id: str) -> List[Dict]:
        """Get tasks for a user with caching"""
        if hashed_user_id not in self._cache:
            self._cache[hashed_user_id] = self.data.get(hashed_user_id, [])
        return self._cache[hashed_user_id]
    
    def _update_user_tasks(self, hashed_user_id: str, tasks: List[Dict]):
        """Update tasks for a user with caching"""
        self.data[hashed_user_id] = tasks
        self._cache[hashed_user_id] = tasks
        self._save_data()
    
    def add_task(self, user_id: str, task: str, deadline: Optional[str] = None) -> bool:
        """Add a task to the user's to-do list with optional deadline"""
        hashed_user_id = self._hash_user_id(user_id)
        
        # Store encrypted actual user ID for DM reminders
        self.data['user_mapping'][hashed_user_id] = self._encrypt_data(user_id)
        
        tasks = self._get_user_tasks(hashed_user_id)
        
        if len(tasks) >= 50:
            return False
        
        task_id = len(tasks) + 1
        hashed_task = self._hash_task_content(task)
        
        task_data = {
            'id': task_id,
            'task_hash': hashed_task,
            'task_encrypted': self._encrypt_data(task),
            'completed': False,
            'created_at': datetime.now().isoformat(),
            'completed_at': None,
            'deadline': deadline,
            'reminder_sent': False
        }
        
        tasks.append(task_data)
        self._update_user_tasks(hashed_user_id, tasks)
        return True
    
    def get_tasks(self, user_id: str) -> List[Dict]:
        """Get all tasks for a user"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self._get_user_tasks(hashed_user_id)
        
        # Decrypt tasks in batch for better performance
        for task in tasks:
            if 'task_encrypted' in task:
                task['task'] = self._decrypt_data(task['task_encrypted'])
        
        return tasks
    
    def get_task(self, user_id: str, task_id: int) -> Optional[Dict]:
        """Get a specific task by ID"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self._get_user_tasks(hashed_user_id)
        
        # Use list comprehension for better performance
        matching_tasks = [task for task in tasks if task['id'] == task_id]
        if not matching_tasks:
            return None
        
        task = matching_tasks[0]
        # Decrypt task content for display
        if 'task_encrypted' in task:
            task['task'] = self._decrypt_data(task['task_encrypted'])
        return task
    
    def complete_task(self, user_id: str, task_id: int) -> bool:
        """Mark a task as completed"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self._get_user_tasks(hashed_user_id)
        
        for task in tasks:
            if task['id'] == task_id and not task['completed']:
                task['completed'] = True
                task['completed_at'] = datetime.now().isoformat()
                self._update_user_tasks(hashed_user_id, tasks)
                return True
        
        return False
    
    def uncomplete_task(self, user_id: str, task_id: int) -> bool:
        """Mark a task as uncompleted"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self._get_user_tasks(hashed_user_id)
        
        for task in tasks:
            if task['id'] == task_id and task['completed']:
                task['completed'] = False
                task['completed_at'] = None
                self._update_user_tasks(hashed_user_id, tasks)
                return True
        
        return False
    
    def remove_task(self, user_id: str, task_id: int) -> bool:
        """Remove a task"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self._get_user_tasks(hashed_user_id)
        
        # Use list comprehension for better performance
        filtered_tasks = [task for task in tasks if task['id'] != task_id]
        
        if len(filtered_tasks) == len(tasks):
            return False  # Task not found
        
        # Reorder remaining task IDs
        for i, task in enumerate(filtered_tasks, 1):
            task['id'] = i
        
        self._update_user_tasks(hashed_user_id, filtered_tasks)
        return True
    
    def clear_completed_tasks(self, user_id: str) -> int:
        """Remove all completed tasks"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self._get_user_tasks(hashed_user_id)
        
        completed_tasks = [task for task in tasks if task['completed']]
        remaining_tasks = [task for task in tasks if not task['completed']]
        
        # Reorder remaining task IDs
        for i, task in enumerate(remaining_tasks, 1):
            task['id'] = i
        
        self._update_user_tasks(hashed_user_id, remaining_tasks)
        return len(completed_tasks)
    
    def clear_all_tasks(self, user_id: str) -> int:
        """Remove all tasks for a user"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self._get_user_tasks(hashed_user_id)
        task_count = len(tasks)
        
        # Clear tasks and cache
        if hashed_user_id in self.data:
            del self.data[hashed_user_id]
        if hashed_user_id in self._cache:
            del self._cache[hashed_user_id]
        
        # Remove user mapping
        if hashed_user_id in self.data['user_mapping']:
            del self.data['user_mapping'][hashed_user_id]
        
        self._save_data()
        return task_count
    
    def add_reminder(self, user_id: str, message: str, reminder_time: str) -> bool:
        """Add a custom reminder"""
        hashed_user_id = self._hash_user_id(user_id)
        
        # Store encrypted actual user ID for DM reminders
        self.data['user_mapping'][hashed_user_id] = self._encrypt_data(user_id)
        
        if hashed_user_id not in self.data['reminders']:
            self.data['reminders'][hashed_user_id] = []
        
        # Check maximum reminders per user
        if len(self.data['reminders'][hashed_user_id]) >= MAX_REMINDERS_PER_USER:
            return False
        
        reminder_id = len(self.data['reminders'][hashed_user_id]) + 1
        hashed_message = self._hash_task_content(message)
        
        reminder_data = {
            'id': reminder_id,
            'message_hash': hashed_message,
            'message_encrypted': self._encrypt_data(message),
            'reminder_time': reminder_time,
            'created_at': datetime.now().isoformat(),
            'sent': False
        }
        
        self.data['reminders'][hashed_user_id].append(reminder_data)
        self._save_data()
        return True
    
    def get_reminders(self, user_id: str) -> List[Dict]:
        """Get all reminders for a user"""
        hashed_user_id = self._hash_user_id(user_id)
        reminders = self.data['reminders'].get(hashed_user_id, [])
        
        # Decrypt reminders in batch
        for reminder in reminders:
            if 'message_encrypted' in reminder:
                reminder['message'] = self._decrypt_data(reminder['message_encrypted'])
        
        return reminders
    
    def delete_reminder(self, user_id: str, reminder_id: int) -> bool:
        """Delete a specific reminder"""
        hashed_user_id = self._hash_user_id(user_id)
        reminders = self.data['reminders'].get(hashed_user_id, [])
        
        # Use list comprehension for better performance
        filtered_reminders = [reminder for reminder in reminders if reminder['id'] != reminder_id]
        
        if len(filtered_reminders) == len(reminders):
            return False  # Reminder not found
        
        # Reorder remaining reminder IDs
        for j, remaining_reminder in enumerate(filtered_reminders, 1):
            remaining_reminder['id'] = j
        
        self.data['reminders'][hashed_user_id] = filtered_reminders
        self._save_data()
        return True
    
    def clear_reminders(self, user_id: str) -> int:
        """Clear all reminders for a user"""
        hashed_user_id = self._hash_user_id(user_id)
        reminder_count = len(self.data['reminders'].get(hashed_user_id, []))
        
        if hashed_user_id in self.data['reminders']:
            del self.data['reminders'][hashed_user_id]
        
        self._save_data()
        return reminder_count
    
    def get_due_reminders(self) -> List[Dict]:
        """Get all reminders that are due to be sent - optimized"""
        due_reminders = []
        now = datetime.now()
        
        for hashed_user_id, reminders in self.data['reminders'].items():
            if hashed_user_id == 'user_mapping':  # Skip the mapping data
                continue
            
            # Filter due reminders in one pass
            due_user_reminders = []
            for reminder in reminders:
                if not reminder.get('sent', False):
                    try:
                        reminder_time = datetime.fromisoformat(reminder['reminder_time'])
                        if reminder_time <= now:
                            # Decrypt message for sending
                            if 'message_encrypted' in reminder:
                                reminder['message'] = self._decrypt_data(reminder['message_encrypted'])
                            
                            due_user_reminders.append(reminder)
                    except ValueError:
                        continue
            
            if due_user_reminders:
                # Get actual user ID for DM
                actual_user_id = None
                if hashed_user_id in self.data['user_mapping']:
                    encrypted_user_id = self.data['user_mapping'][hashed_user_id]
                    actual_user_id = self._decrypt_data(encrypted_user_id)
                
                for reminder in due_user_reminders:
                    due_reminders.append({
                        'user_id': actual_user_id,
                        'hashed_user_id': hashed_user_id,
                        'reminder': reminder
                    })
        
        return due_reminders
    
    def get_upcoming_deadlines(self, hours_ahead: int = DEADLINE_REMINDER_HOURS) -> List[Dict]:
        """Get all tasks with deadlines approaching within the specified hours - optimized"""
        upcoming_tasks = []
        now = datetime.now()
        cutoff_time = now + timedelta(hours=hours_ahead)
        
        for hashed_user_id, tasks in self.data.items():
            # Skip the user_mapping and reminders keys
            if hashed_user_id in ['user_mapping', 'reminders']:
                continue
            
            # Filter tasks with upcoming deadlines in one pass
            upcoming_user_tasks = []
            for task in tasks:
                if (task.get('deadline') and 
                    not task['completed'] and 
                    not task.get('reminder_sent', False)):
                    
                    try:
                        deadline = datetime.fromisoformat(task['deadline'])
                        if now <= deadline <= cutoff_time:
                            # Decrypt task content for the reminder
                            if 'task_encrypted' in task:
                                task['task'] = self._decrypt_data(task['task_encrypted'])
                            
                            upcoming_user_tasks.append(task)
                    except ValueError:
                        # Skip tasks with invalid deadline format
                        continue
            
            if upcoming_user_tasks:
                # Get the actual user ID from mapping
                actual_user_id = None
                if hashed_user_id in self.data['user_mapping']:
                    encrypted_user_id = self.data['user_mapping'][hashed_user_id]
                    actual_user_id = self._decrypt_data(encrypted_user_id)
                
                for task in upcoming_user_tasks:
                    upcoming_tasks.append({
                        'user_id': actual_user_id,  # Use actual user ID for reminders
                        'hashed_user_id': hashed_user_id,  # Keep hashed version for database operations
                        'task': task
                    })
        
        return upcoming_tasks
    
    def mark_reminder_sent(self, hashed_user_id: str, reminder_id: int) -> bool:
        """Mark a reminder as sent"""
        reminders = self.data['reminders'].get(hashed_user_id, [])
        
        for reminder in reminders:
            if reminder['id'] == reminder_id:
                reminder['sent'] = True
                self._save_data()
                return True
        
        return False
    
    def mark_deadline_reminder_sent(self, hashed_user_id: str, task_id: int) -> bool:
        """Mark that a deadline reminder has been sent for a task"""
        if hashed_user_id not in self.data:
            return False
        
        for task in self.data[hashed_user_id]:
            if task['id'] == task_id:
                task['reminder_sent'] = True
                self._save_data()
                return True
        
        return False
    
    def force_save(self):
        """Force save the database immediately"""
        self._save_data(force=True) 