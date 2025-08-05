import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_PREFIX = '!'

# Database Configuration
DATABASE_FILE = 'todo_database.json'

# Encryption Configuration
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'your-secret-key-change-this-in-production')
ENABLE_ENCRYPTION = os.getenv('ENABLE_ENCRYPTION', 'true').lower() == 'true'

# Bot Settings
MAX_TASKS_PER_USER = 50
MAX_TASK_LENGTH = 200

# Performance Settings
REMINDER_CHECK_INTERVAL = int(os.getenv('REMINDER_CHECK_INTERVAL', '2'))  # minutes
DATABASE_SAVE_DEBOUNCE = int(os.getenv('DATABASE_SAVE_DEBOUNCE', '30'))  # seconds
MAX_REMINDERS_PER_USER = 20
DEADLINE_REMINDER_HOURS = 12

# Cache Settings
CACHE_SIZE = int(os.getenv('CACHE_SIZE', '128'))
MAX_CONCURRENT_REMINDERS = int(os.getenv('MAX_CONCURRENT_REMINDERS', '10'))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s' 