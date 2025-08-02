# 🤖 Discord To-Do Bot

A feature-rich Discord bot for managing personal to-do lists with encrypted storage, task deadlines, custom reminders, and privacy protection.

## ✨ Features

### 📋 **To-Do List Management**
- ✅ **Add tasks** - Create new tasks with `!add <task>`
- ✅ **Add tasks with deadlines** - Create tasks with deadlines using `!add <task> | <deadline>`
- 📝 **List tasks** - View your personal to-do list with deadline status
- ✅ **Complete tasks** - Mark tasks as completed
- ⏳ **Uncomplete tasks** - Mark completed tasks as pending
- 🗑️ **Remove tasks** - Delete specific tasks from your list
- 🧹 **Clear completed** - Remove all completed tasks at once
- 🗑️ **Clear all** - Remove all tasks (use with caution!)

### **Dual Reminder System**
- **Custom reminders** - Create standalone reminders with `!remindme <message> | <time>`
- **Task deadlines** - Set deadlines for tasks with automatic 12-hour reminders
- **List reminders** - View all your active reminders
- **Delete reminders** - Remove specific reminders
- **Clear reminders** - Remove all your reminders at once
- **Private delivery** - All reminders sent via DM only

### 🔒 **Privacy & Security**
- **Encrypted storage** - All data encrypted with AES-256
- **User isolation** - Each user has their own private to-do list
- **Data hashing** - User IDs and content hashed for additional privacy
- 🛡**Secure reminders** - Reminder messages encrypted and hashed

### 🎯 **User Experience**
- **Welcome messages** - Bot introduces itself when joining servers
- **DM support** - Interact with the bot via private messages
- **Progress tracking** - See completion status of your tasks
- **Responsive reminders** - Checked every minute for immediate delivery
- **Rich embeds** - Beautiful, organized display with colors and emojis

## 🚀 Quick Start

### 1. **Prerequisites**
- Python 3.8 or higher
- Discord account and bot token

### 2. **Installation**

```bash
# Clone or download the bot files
# Navigate to the bot directory
cd "Discord Bot"

# Install dependencies
pip install -r requirements.txt
```

### 3. **Discord Bot Setup**

1. **Create a Discord Application:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application"
   - Give it a name (e.g., "To-Do Bot")

2. **Create a Bot:**
   - Go to the "Bot" section
   - Click "Add Bot"
   - Copy the bot token

3. **Set Bot Permissions:**
   - Go to "OAuth2" → "URL Generator"
   - Select scopes: `bot`, `applications.commands`
   - Select bot permissions:
     - ✅ Send Messages
     - ✅ Use Slash Commands
     - ✅ Embed Links
     - ✅ Read Message History
   - Copy the generated URL and invite the bot to your server

4. **Enable Privileged Intents:**
   - Go to "Bot" section
   - Enable these intents:
     - ✅ **MESSAGE CONTENT INTENT** (Required)
     - ✅ **SERVER MEMBERS INTENT** (Recommended)
     - ✅ **PRESENCE INTENT** (Optional)

### 4. **Configuration**

1. **Create `.env` file:**
```bash
# Copy the example file
copy env_example.txt .env
```

2. **Edit `.env` file:**
```env
# Discord Bot Configuration
DISCORD_TOKEN=your_bot_token_here

# Encryption Configuration (Optional but recommended)
ENCRYPTION_KEY=your-strong-encryption-key-here
ENABLE_ENCRYPTION=true
```

### 5. **Run the Bot**

```bash
python bot.py
```

## 📖 Commands

### 📋 **To-Do Commands**

| Command | Description | Example |
|---------|-------------|---------|
| `!add <task>` | Add a new task | `!add Buy groceries` |
| `!add <task> \| <deadline>` | Add task with deadline | `!add Buy groceries \| in 2 hours` |
| `!list` | Show your to-do list | `!list` |
| `!deadline <id> <deadline>` | Set deadline for a task | `!deadline 1 in 3 days` |
| `!complete <id>` | Mark task as completed | `!complete 1` |
| `!uncomplete <id>` | Mark task as uncompleted | `!uncomplete 1` |
| `!remove <id>` | Remove a task | `!remove 1` |
| `!clear` | Remove all completed tasks | `!clear` |
| `!clearall` | Remove all tasks | `!clearall` |

### ⏰ **Reminder Commands**

| Command | Description | Example |
|---------|-------------|---------|
| `!remindme <message> \| <time>` | Set a custom reminder | `!remindme Take medicine \| in 2 hours` |
| `!reminders` | Show your active reminders | `!reminders` |
| `!delreminder <id>` | Delete a specific reminder | `!delreminder 1` |
| `!clearreminders` | Delete all your reminders | `!clearreminders` |

### 📚 **Help Commands**

| Command | Description |
|---------|-------------|
| `!help` | Show detailed help information |

## ⏰ **Time Formats**

The bot supports various time formats for both deadlines and reminders:

### **Relative Time**
- `in 2 hours` - 2 hours from now
- `in 30 minutes` - 30 minutes from now
- `in 3 days` - 3 days from now
- `in 1 week` - 1 week from now
- `in 2 months` - 2 months from now

### **Specific Time**
- `14:30` - 2:30 PM today (or tomorrow if time has passed)
- `09:00` - 9:00 AM today/tomorrow

### **Specific Date & Time**
- `2024-12-31 17:00` - December 31, 2024 at 5:00 PM
- `12/31/2024 17:00` - Same as above (MM/DD/YYYY format)
- `31/12/2024 17:00` - Same as above (DD/MM/YYYY format)

### **Date Only**
- `2024-12-31` - December 31, 2024 at 9:00 AM
- `12/31/2024` - Same as above (MM/DD/YYYY format)
- `31/12/2024` - Same as above (DD/MM/YYYY format)

## 🎯 **Usage Examples**

### **Task Management with Deadlines**
```
!add Buy groceries | in 2 hours
!add Complete project documentation | 2024-12-31 17:00
!add Call the dentist | in 3 days
!add Submit report | 14:30
!deadline 1 in 1 week
!list
```

### **Custom Reminders**
```
!remindme Take medicine | in 30 minutes
!remindme Call dentist | 14:30
!remindme Submit report | 2024-12-31 17:00
!remindme Meeting | in 1 hour
!reminders
```

### **Task Management**
```
!list                    # View all tasks with deadline status
!complete 1             # Mark task #1 as completed
!uncomplete 1           # Mark task #1 as uncompleted
!remove 2               # Remove task #2
!clear                  # Remove all completed tasks
```

## 🔒 **Privacy & Security Features**

### **Data Encryption**
- All data is encrypted using AES-256 (Fernet)
- Encryption key derived from your `ENCRYPTION_KEY`
- Database file is completely encrypted

### **Data Hashing**
- User IDs are hashed using HMAC-SHA256
- Task and reminder content are hashed
- Provides additional privacy even if encryption is compromised

### **User Isolation**
- Each user has their own private to-do list
- Users cannot see each other's tasks or reminders
- All data is user-specific and isolated

### **Private Reminders**
- Reminders are sent via private DM only
- No reminder content is visible in server channels
- Secure user ID mapping for DM delivery

## 🛠️ **Technical Details**

### **File Structure**
```
Discord Bot/
├── bot.py              # Main bot file
├── todo_commands.py    # Command implementations
├── database.py         # Database and encryption logic
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (create this)
├── .gitignore         # Git ignore file
└── README.md          # This file
```

### **Dependencies**
- `discord.py>=2.4.0` - Discord bot library
- `python-dotenv==1.0.0` - Environment variable management
- `cryptography==41.0.7` - Encryption and hashing

### **Database Structure**
- JSON-based storage with encryption
- Separate sections for tasks and reminders
- Encrypted user ID mapping for DM functionality

## 🚨 **Troubleshooting**

### **Common Issues**

**1. Bot won't start**
- Check your Discord token in `.env` file
- Ensure all dependencies are installed
- Verify bot has proper permissions

**2. Commands not working**
- Make sure bot has "Message Content Intent" enabled
- Check bot has "Send Messages" permission
- Verify bot is online and connected

**3. Reminders not being sent**
- Check if user has DMs enabled
- Verify bot has proper intents enabled
- Check bot logs for error messages

**4. Encryption errors**
- Ensure `cryptography` package is installed
- Check your `ENCRYPTION_KEY` is set correctly
- Try setting `ENABLE_ENCRYPTION=false` temporarily

### **Getting Help**
- Check the bot logs for error messages
- Verify all configuration steps are completed
- Ensure Discord Developer Portal settings are correct

## 🔧 **Advanced Configuration**

### **Environment Variables**
```env
# Required
DISCORD_TOKEN=your_bot_token_here

# Optional (recommended for production)
ENCRYPTION_KEY=your-strong-encryption-key-here
ENABLE_ENCRYPTION=true
```

### **Bot Settings**
- Maximum tasks per user: 50
- Maximum reminders per user: 20
- Maximum task length: 200 characters
- Maximum reminder message length: 200 characters
- Reminder check interval: 1 minute
- Deadline reminder: 12 hours before due

## 📝 **License**

This project is open source and available under the MIT License.

## 🤝 **Contributing**

Feel free to submit issues, feature requests, or pull requests to improve the bot!

---

**Enjoy your encrypted, private to-do list management with deadlines and reminders!** 
