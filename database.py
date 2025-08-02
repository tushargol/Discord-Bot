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
from config import DATABASE_FILE, ENCRYPTION_KEY, ENABLE_ENCRYPTION

class TodoDatabase:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.fernet = self._setup_encryption()
        self.data = self._load_data()
        if 'user_mapping' not in self.data:
            self.data['user_mapping'] = {}
        if 'reminders' not in self.data:
            self.data['reminders'] = {}
    
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
    
    def _save_data(self):
        """Save data to file with encryption"""
        try:
            json_content = json.dumps(self.data, indent=2, ensure_ascii=False)
            encrypted_content = self._encrypt_data(json_content)
            
            with open(self.db_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_content)
        except Exception as e:
            print(f"Error saving database: {e}")
    
    def add_task(self, user_id: str, task: str, deadline: Optional[str] = None) -> bool:
        """Add a task to the user's to-do list with optional deadline"""
        hashed_user_id = self._hash_user_id(user_id)
        
        # Store encrypted actual user ID for DM reminders
        self.data['user_mapping'][hashed_user_id] = self._encrypt_data(user_id)
        
        if hashed_user_id not in self.data:
            self.data[hashed_user_id] = []
        
        if len(self.data[hashed_user_id]) >= 50:
            return False
        
        task_id = len(self.data[hashed_user_id]) + 1
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
        
        self.data[hashed_user_id].append(task_data)
        self._save_data()
        return True
    
    def get_tasks(self, user_id: str) -> List[Dict]:
        """Get all tasks for a user"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self.data.get(hashed_user_id, [])
        
        for task in tasks:
            if 'task_encrypted' in task:
                task['task'] = self._decrypt_data(task['task_encrypted'])
        
        return tasks
    
    def get_task(self, user_id: str, task_id: int) -> Optional[Dict]:
        """Get a specific task by ID"""
        hashed_user_id = self._hash_user_id(user_id)
        
        if hashed_user_id not in self.data:
            return None
        
        for task in self.data[hashed_user_id]:
            if task['id'] == task_id:
                # Decrypt task content for display
                if 'task_encrypted' in task:
                    task['task'] = self._decrypt_data(task['task_encrypted'])
                return task
        
        return None
    
    def complete_task(self, user_id: str, task_id: int) -> bool:
        """Mark a task as completed"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self.data.get(hashed_user_id, [])
        
        for task in tasks:
            if task['id'] == task_id and not task['completed']:
                task['completed'] = True
                task['completed_at'] = datetime.now().isoformat()
                self._save_data()
                return True
        
        return False
    
    def uncomplete_task(self, user_id: str, task_id: int) -> bool:
        """Mark a task as uncompleted"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self.data.get(hashed_user_id, [])
        
        for task in tasks:
            if task['id'] == task_id and task['completed']:
                task['completed'] = False
                task['completed_at'] = None
                self._save_data()
                return True
        
        return False
    
    def remove_task(self, user_id: str, task_id: int) -> bool:
        """Remove a task"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self.data.get(hashed_user_id, [])
        
        for i, task in enumerate(tasks):
            if task['id'] == task_id:
                del tasks[i]
                # Reorder remaining task IDs
                for j, remaining_task in enumerate(tasks, 1):
                    remaining_task['id'] = j
                self._save_data()
                return True
        
        return False
    
    def clear_completed_tasks(self, user_id: str) -> int:
        """Remove all completed tasks"""
        hashed_user_id = self._hash_user_id(user_id)
        tasks = self.data.get(hashed_user_id, [])
        
        completed_tasks = [task for task in tasks if task['completed']]
        self.data[hashed_user_id] = [task for task in tasks if not task['completed']]
        
        # Reorder remaining task IDs
        for i, task in enumerate(self.data[hashed_user_id], 1):
            task['id'] = i
        
        self._save_data()
        return len(completed_tasks)
    
    def clear_all_tasks(self, user_id: str) -> int:
        """Remove all tasks for a user"""
        hashed_user_id = self._hash_user_id(user_id)
        task_count = len(self.data.get(hashed_user_id, []))
        
        if hashed_user_id in self.data:
            del self.data[hashed_user_id]
        
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
        
        # Check maximum reminders per user (20)
        if len(self.data['reminders'][hashed_user_id]) >= 20:
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
        
        for reminder in reminders:
            if 'message_encrypted' in reminder:
                reminder['message'] = self._decrypt_data(reminder['message_encrypted'])
        
        return reminders
    
    def delete_reminder(self, user_id: str, reminder_id: int) -> bool:
        """Delete a specific reminder"""
        hashed_user_id = self._hash_user_id(user_id)
        reminders = self.data['reminders'].get(hashed_user_id, [])
        
        for i, reminder in enumerate(reminders):
            if reminder['id'] == reminder_id:
                del reminders[i]
                # Reorder remaining reminder IDs
                for j, remaining_reminder in enumerate(reminders, 1):
                    remaining_reminder['id'] = j
                self._save_data()
                return True
        
        return False
    
    def clear_reminders(self, user_id: str) -> int:
        """Clear all reminders for a user"""
        hashed_user_id = self._hash_user_id(user_id)
        reminder_count = len(self.data['reminders'].get(hashed_user_id, []))
        
        if hashed_user_id in self.data['reminders']:
            del self.data['reminders'][hashed_user_id]
        
        self._save_data()
        return reminder_count
    
    def get_due_reminders(self) -> List[Dict]:
        """Get all reminders that are due to be sent"""
        due_reminders = []
        now = datetime.now()
        
        for hashed_user_id, reminders in self.data['reminders'].items():
            if hashed_user_id == 'user_mapping':  # Skip the mapping data
                continue
            
            for reminder in reminders:
                if not reminder.get('sent', False):
                    try:
                        reminder_time = datetime.fromisoformat(reminder['reminder_time'])
                        if reminder_time <= now:
                            # Decrypt message for sending
                            if 'message_encrypted' in reminder:
                                reminder['message'] = self._decrypt_data(reminder['message_encrypted'])
                            
                            # Get actual user ID for DM
                            actual_user_id = None
                            if hashed_user_id in self.data['user_mapping']:
                                encrypted_user_id = self.data['user_mapping'][hashed_user_id]
                                actual_user_id = self._decrypt_data(encrypted_user_id)
                            
                            due_reminders.append({
                                'user_id': actual_user_id,
                                'hashed_user_id': hashed_user_id,
                                'reminder': reminder
                            })
                    except ValueError:
                        continue
        
        return due_reminders
    
    def get_upcoming_deadlines(self, hours_ahead: int = 12) -> List[Dict]:
        """Get all tasks with deadlines approaching within the specified hours"""
        upcoming_tasks = []
        now = datetime.now()
        cutoff_time = now + timedelta(hours=hours_ahead)
        
        for hashed_user_id, tasks in self.data.items():
            # Skip the user_mapping and reminders keys
            if hashed_user_id in ['user_mapping', 'reminders']:
                continue
                
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
                            
                            # Get the actual user ID from mapping
                            actual_user_id = None
                            if hashed_user_id in self.data['user_mapping']:
                                encrypted_user_id = self.data['user_mapping'][hashed_user_id]
                                actual_user_id = self._decrypt_data(encrypted_user_id)
                            
                            upcoming_tasks.append({
                                'user_id': actual_user_id,  # Use actual user ID for reminders
                                'hashed_user_id': hashed_user_id,  # Keep hashed version for database operations
                                'task': task
                            })
                    except ValueError:
                        # Skip tasks with invalid deadline format
                        continue
        
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