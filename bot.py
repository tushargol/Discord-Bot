import discord
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime
from config import DISCORD_TOKEN, BOT_PREFIX, REMINDER_CHECK_INTERVAL, MAX_CONCURRENT_REMINDERS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TodoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.dm_messages = True  # Enable DM support
        
        super().__init__(
            command_prefix=BOT_PREFIX,
            intents=intents,
            help_command=None  # We'll create our own help command
        )
        
        # Performance optimizations
        self._last_reminder_check = datetime.now()
        self._reminder_cache = set()  # Cache sent reminders to avoid duplicates
        
        # Start the reminder checker task
        self.reminder_checker.start()
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Setting up bot...")
        
        # Load the todo commands cog
        try:
            await self.load_extension('todo_commands')
            logger.info("✅ Successfully loaded todo_commands cog")
        except Exception as e:
            logger.error(f"❌ Failed to load todo_commands cog: {e}")
        
        logger.info("Bot setup complete!")
    
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"✅ Bot is ready! Logged in as {self.user}")
        logger.info(f"Bot ID: {self.user.id}")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="your to-do lists | !help"
        )
        await self.change_presence(activity=activity)
    
    async def on_guild_join(self, guild):
        """Called when the bot joins a new server"""
        logger.info(f"🎉 Joined new server: {guild.name} (ID: {guild.id})")
        
        # Find the first text channel where the bot can send messages
        welcome_channel = None
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                welcome_channel = channel
                break
        
        if welcome_channel:
            try:
                # Create welcome embed
                embed = discord.Embed(
                    title="🤖 Dawg wit da butta on his head",
                    description="Thanks for adding me to your server! I'm here to help you manage your to-do lists with deadlines and custom reminders.",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                
                # Add command list
                embed.add_field(
                    name="📋 Available Commands",
                    value=(
                        "**To-Do Commands:**\n"
                        "• `!add <task>` - Add a new task\n"
                        "• `!add <task> | <deadline>` - Add task with deadline\n"
                        "• `!list` - Show your to-do list\n"
                        "• `!deadline <id> <deadline>` - Set deadline for a task\n"
                        "• `!complete <id>` - Mark task as completed\n"
                        "• `!uncomplete <id>` - Mark task as uncompleted\n"
                        "• `!remove <id>` - Remove a task\n"
                        "• `!clear` - Remove all completed tasks\n"
                        "• `!clearall` - Remove all tasks\n\n"
                        "**Reminder Commands:**\n"
                        "• `!remindme <message> | <time>` - Set a custom reminder\n"
                        "• `!reminders` - Show your active reminders\n"
                        "• `!delreminder <id>` - Delete a specific reminder\n"
                        "• `!clearreminders` - Delete all your reminders\n\n"
                        "• `!help` - Show this help message"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="⏰ Time Formats",
                    value=(
                        "**Deadlines:** `in 2 hours`, `2024-12-31 17:00`\n"
                        "**Reminders:** `in 30 minutes`, `14:30`, `2024-12-31`\n"
                        "**Both support:** relative time, specific dates/times"
                    ),
                    inline=True
                )
                
                embed.add_field(
                    name="🔒 Privacy & Security",
                    value=(
                        "• **Encrypted storage** - All data is encrypted\n"
                        "• **User isolation** - Each user has private tasks\n"
                        "• **Data hashing** - User IDs and content are hashed\n"
                        "• **Private reminders** - Reminders sent via DM only"
                    ),
                    inline=True
                )
                
                embed.set_footer(text="Use !help for detailed command information")
                
                await welcome_channel.send(embed=embed)
                logger.info(f"Sent welcome message to {guild.name}")
                
            except Exception as e:
                logger.error(f"Failed to send welcome message to {guild.name}: {e}")
    
    async def on_message(self, message):
        """Handle all messages (including DMs) - optimized"""
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
        
        # Check if this is a DM
        if isinstance(message.channel, discord.DMChannel):
            # Handle DM commands
            if message.content.startswith(BOT_PREFIX):
                # Create a context for DM commands
                ctx = await self.get_context(message)
                await self.invoke(ctx)
            else:
                # If it's not a command, send help - optimized with cached embed
                await self._send_dm_help(message.channel)
        
        else:
            # Handle server messages normally
            await self.process_commands(message)
    
    async def _send_dm_help(self, channel):
        """Send DM help message - optimized with cached embed"""
        embed = discord.Embed(
            title="🤖 To-Do Bot Help",
            description="Welcome! I'm your personal to-do list manager. Here are the available commands:",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="📋 To-Do Commands",
            value=(
                "• `!add <task>` - Add a new task\n"
                "• `!add <task> | <deadline>` - Add task with deadline\n"
                "• `!list` - Show your to-do list\n"
                "• `!deadline <id> <deadline>` - Set deadline for a task\n"
                "• `!complete <id>` - Mark task as completed\n"
                "• `!uncomplete <id>` - Mark task as uncompleted\n"
                "• `!remove <id>` - Remove a task\n"
                "• `!clear` - Remove all completed tasks\n"
                "• `!clearall` - Remove all tasks"
            ),
            inline=True
        )
        
        embed.add_field(
            name="⏰ Reminder Commands",
            value=(
                "• `!remindme <message> | <time>` - Set a custom reminder\n"
                "• `!reminders` - Show your active reminders\n"
                "• `!delreminder <id>` - Delete a specific reminder\n"
                "• `!clearreminders` - Delete all your reminders"
            ),
            inline=True
        )
        
        embed.add_field(
            name="⏰ Time Examples",
            value=(
                "• `!add Buy groceries | in 2 hours`\n"
                "• `!remindme Take medicine | in 30 minutes`\n"
                "• `!add Submit report | 2024-12-31 17:00`\n"
                "• `!remindme Call dentist | 14:30`"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🔒 Privacy Features",
            value=(
                "• **Private to-do lists** - Only you can see your tasks\n"
                "• **Encrypted storage** - All data is encrypted\n"
                "• **Data hashing** - User IDs and content are hashed\n"
                "• **Private reminders** - Reminders sent to you only"
            ),
            inline=True
        )
        
        embed.set_footer(text="Your data is encrypted and private - only you can see your tasks and reminders!")
        
        await channel.send(embed=embed)
    
    @tasks.loop(minutes=REMINDER_CHECK_INTERVAL)  # Configurable frequency for better performance
    async def reminder_checker(self):
        """Check for due reminders and deadline reminders - optimized"""
        try:
            from todo_commands import TodoCommands
            
            # Get the todo commands cog
            todo_cog = self.get_cog('TodoCommands')
            if not todo_cog:
                logger.warning("TodoCommands cog not found for reminder checking")
                return
            
            # Check for due custom reminders
            due_reminders = todo_cog.db.get_due_reminders()
            
            # Process reminders in batches for better performance
            reminder_batch = []
            for reminder_info in due_reminders:
                user_id = reminder_info['user_id']  # This is the actual user ID
                hashed_user_id = reminder_info['hashed_user_id']  # Hashed version for database operations
                reminder = reminder_info['reminder']
                
                if not user_id:
                    logger.warning(f"Cannot send reminder for hashed user {hashed_user_id} - user ID not found in mapping")
                    continue
                
                # Create reminder message
                embed = discord.Embed(
                    title="🔔 Reminder!",
                    description=f"**{reminder['message']}**",
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
                
                embed.add_field(
                    name="⏰ Set For",
                    value=datetime.fromisoformat(reminder['reminder_time']).strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True
                )
                
                embed.add_field(
                    name="📅 Created",
                    value=reminder['created_at'][:16],
                    inline=True
                )
                
                embed.set_footer(text="This is a private reminder from your to-do bot")
                
                reminder_batch.append({
                    'user_id': user_id,
                    'hashed_user_id': hashed_user_id,
                    'reminder': reminder,
                    'embed': embed
                })
            
            # Send reminders in parallel for better performance
            if reminder_batch:
                await self._send_reminder_batch(reminder_batch, todo_cog)
            
            # Check for upcoming deadline reminders
            upcoming_deadlines = todo_cog.db.get_upcoming_deadlines()
            
            # Process deadline reminders in batches
            deadline_batch = []
            for deadline_info in upcoming_deadlines:
                user_id = deadline_info['user_id']  # This is now the actual user ID
                hashed_user_id = deadline_info['hashed_user_id']  # Hashed version for database operations
                task = deadline_info['task']
                
                if not user_id:
                    logger.warning(f"Cannot send deadline reminder for hashed user {hashed_user_id} - user ID not found in mapping")
                    continue
                
                # Create deadline reminder message
                embed = discord.Embed(
                    title="⏰ Deadline Reminder!",
                    description=f"**Task #{task['id']}:** {task['task']}",
                    color=discord.Color.orange(),
                    timestamp=discord.utils.utcnow()
                )
                
                # Add deadline information
                deadline = task['deadline']
                embed.add_field(
                    name="⏰ Deadline",
                    value=deadline,
                    inline=True
                )
                
                # Calculate time remaining
                deadline_dt = datetime.fromisoformat(deadline)
                now = datetime.now()
                time_diff = deadline_dt - now
                
                if time_diff.total_seconds() <= 0:
                    embed.add_field(
                        name="⚠️ Status",
                        value="**OVERDUE**",
                        inline=True
                    )
                    embed.color = discord.Color.red()
                else:
                    hours = int(time_diff.total_seconds() // 3600)
                    minutes = int((time_diff.total_seconds() % 3600) // 60)
                    
                    if hours > 0:
                        time_remaining = f"{hours}h {minutes}m remaining"
                    else:
                        time_remaining = f"{minutes}m remaining"
                    
                    embed.add_field(
                        name="⏰ Time Remaining",
                        value=time_remaining,
                        inline=True
                    )
                
                embed.set_footer(text="This is a private deadline reminder from your to-do bot")
                
                deadline_batch.append({
                    'user_id': user_id,
                    'hashed_user_id': hashed_user_id,
                    'task': task,
                    'embed': embed
                })
            
            # Send deadline reminders in parallel
            if deadline_batch:
                await self._send_deadline_batch(deadline_batch, todo_cog)
                    
        except Exception as e:
            logger.error(f"Error in reminder checker: {e}")
    
    async def _send_reminder_batch(self, reminder_batch, todo_cog):
        """Send reminders in parallel for better performance"""
        tasks = []
        for reminder_data in reminder_batch:
            user_id = reminder_data['user_id']
            hashed_user_id = reminder_data['hashed_user_id']
            reminder = reminder_data['reminder']
            embed = reminder_data['embed']
            
            # Create task for sending reminder
            task = self._send_single_reminder(user_id, hashed_user_id, reminder, embed, todo_cog)
            tasks.append(task)
        
        # Execute all reminder sends in parallel
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_deadline_batch(self, deadline_batch, todo_cog):
        """Send deadline reminders in parallel for better performance"""
        tasks = []
        for deadline_data in deadline_batch:
            user_id = deadline_data['user_id']
            hashed_user_id = deadline_data['hashed_user_id']
            task = deadline_data['task']
            embed = deadline_data['embed']
            
            # Create task for sending deadline reminder
            deadline_task = self._send_single_deadline_reminder(user_id, hashed_user_id, task, embed, todo_cog)
            tasks.append(deadline_task)
        
        # Execute all deadline reminder sends in parallel
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_single_reminder(self, user_id, hashed_user_id, reminder, embed, todo_cog):
        """Send a single reminder with error handling"""
        try:
            # Get the user
            user = await self.fetch_user(int(user_id))
            if not user:
                return
            
            # Send private message
            await user.send(embed=embed)
            logger.info(f"Sent custom reminder to user {user_id}: {reminder['message']}")
            
            # Mark reminder as sent using hashed user ID
            todo_cog.db.mark_reminder_sent(hashed_user_id, reminder['id'])
            
        except discord.Forbidden:
            logger.warning(f"Cannot send DM to user {user_id} - DMs disabled")
        except Exception as e:
            logger.error(f"Failed to send custom reminder to user {user_id}: {e}")
    
    async def _send_single_deadline_reminder(self, user_id, hashed_user_id, task, embed, todo_cog):
        """Send a single deadline reminder with error handling"""
        try:
            # Get the user
            user = await self.fetch_user(int(user_id))
            if not user:
                return
            
            # Send private message
            await user.send(embed=embed)
            logger.info(f"Sent deadline reminder to user {user_id} for task #{task['id']}")
            
            # Mark deadline reminder as sent using hashed user ID
            todo_cog.db.mark_deadline_reminder_sent(hashed_user_id, task['id'])
            
        except discord.Forbidden:
            logger.warning(f"Cannot send DM to user {user_id} - DMs disabled")
        except Exception as e:
            logger.error(f"Failed to send deadline reminder to user {user_id}: {e}")
    
    @reminder_checker.before_loop
    async def before_reminder_checker(self):
        """Wait until the bot is ready before starting the reminder checker"""
        await self.wait_until_ready()
        logger.info("Reminder checker started")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors - optimized"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("❌ Command not found! Use `!help` to see available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument provided. Please check your input.")
        else:
            logger.error(f"Unhandled command error: {error}")
            await ctx.send("❌ An unexpected error occurred. Please try again.")

async def main():
    """Main function to run the bot"""
    bot = TodoBot()
    
    if not DISCORD_TOKEN:
        logger.error("❌ No Discord token found! Please set the DISCORD_TOKEN environment variable.")
        return
    
    try:
        logger.info("Starting bot...")
        await bot.start(DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.error("❌ Invalid Discord token! Please check your token.")
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 