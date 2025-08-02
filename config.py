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