import discord
import re
from discord.ext import commands
from database import TodoDatabase
from config import MAX_TASK_LENGTH
from datetime import datetime, timedelta

class TodoCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = TodoDatabase()
    
    def _parse_deadline(self, deadline_str: str) -> str:
        """Parse deadline string and return ISO format datetime"""
        deadline_str = deadline_str.strip().lower()
        now = datetime.now()
        
        # Parse relative time formats
        if deadline_str.startswith('in '):
            time_part = deadline_str[3:]  # Remove 'in '
            
            # Parse hours
            if 'hour' in time_part:
                hours = int(re.search(r'(\d+)\s*hour', time_part).group(1))
                return (now + timedelta(hours=hours)).isoformat()
            
            # Parse days
            elif 'day' in time_part:
                days = int(re.search(r'(\d+)\s*day', time_part).group(1))
                return (now + timedelta(days=days)).isoformat()
            
            # Parse weeks
            elif 'week' in time_part:
                weeks = int(re.search(r'(\d+)\s*week', time_part).group(1))
                return (now + timedelta(weeks=weeks)).isoformat()
            
            # Parse minutes
            elif 'minute' in time_part:
                minutes = int(re.search(r'(\d+)\s*minute', time_part).group(1))
                return (now + timedelta(minutes=minutes)).isoformat()
        
        # Parse absolute time formats
        try:
            # Try parsing as "YYYY-MM-DD HH:MM"
            if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', deadline_str):
                return datetime.strptime(deadline_str, '%Y-%m-%d %H:%M').isoformat()
            
            # Try parsing as "MM/DD/YYYY HH:MM"
            elif re.match(r'\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}', deadline_str):
                return datetime.strptime(deadline_str, '%m/%d/%Y %H:%M').isoformat()
            
            # Try parsing as "DD/MM/YYYY HH:MM"
            elif re.match(r'\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}', deadline_str):
                return datetime.strptime(deadline_str, '%d/%m/%Y %H:%M').isoformat()
            
            # Try parsing as "HH:MM" (today)
            elif re.match(r'\d{1,2}:\d{2}', deadline_str):
                time_obj = datetime.strptime(deadline_str, '%H:%M').time()
                deadline = now.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
                if deadline <= now:
                    deadline += timedelta(days=1)  # If time has passed, set for tomorrow
                return deadline.isoformat()
            
            # Try parsing as "YYYY-MM-DD"
            elif re.match(r'\d{4}-\d{2}-\d{2}', deadline_str):
                return datetime.strptime(deadline_str, '%Y-%m-%d').replace(hour=23, minute=59).isoformat()
            
            # Try parsing as "MM/DD/YYYY"
            elif re.match(r'\d{1,2}/\d{1,2}/\d{4}', deadline_str):
                return datetime.strptime(deadline_str, '%m/%d/%Y').replace(hour=23, minute=59).isoformat()
            
            # Try parsing as "DD/MM/YYYY"
            elif re.match(r'\d{1,2}/\d{1,2}/\d{4}', deadline_str):
                return datetime.strptime(deadline_str, '%d/%m/%Y').replace(hour=23, minute=59).isoformat()
            
        except ValueError:
            pass
        
        # If no format matches, raise an error
        raise ValueError(f"Invalid deadline format: {deadline_str}")
    
    def _format_deadline(self, deadline_iso: str) -> str:
        """Format deadline for display"""
        try:
            deadline = datetime.fromisoformat(deadline_iso)
            return deadline.strftime('%Y-%m-%d %H:%M')
        except ValueError:
            return "Invalid deadline"
    
    def _get_deadline_status(self, deadline_iso: str) -> tuple:
        """Get deadline status and time remaining"""
        try:
            deadline = datetime.fromisoformat(deadline_iso)
            now = datetime.now()
            
            if deadline <= now:
                return "overdue", "Overdue"
            
            time_diff = deadline - now
            days = time_diff.days
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60
            
            if days > 0:
                return "upcoming", f"{days}d {hours}h remaining"
            elif hours > 0:
                return "upcoming", f"{hours}h {minutes}m remaining"
            else:
                return "urgent", f"{minutes}m remaining"
                
        except ValueError:
            return "invalid", "Invalid deadline"
    
    def _parse_reminder_time(self, time_str: str) -> datetime:
        """Parse various time formats for reminders"""
        time_str = time_str.lower().strip()
        now = datetime.now()
        
        # Handle "in X time" format
        if time_str.startswith('in '):
            time_str = time_str[3:]  # Remove "in "
            
            # Parse different time units
            time_patterns = [
                (r'(\d+)\s*years?', lambda x: timedelta(days=x*365)),
                (r'(\d+)\s*months?', lambda x: timedelta(days=x*30)),
                (r'(\d+)\s*weeks?', lambda x: timedelta(weeks=x)),
                (r'(\d+)\s*days?', lambda x: timedelta(days=x)),
                (r'(\d+)\s*hours?', lambda x: timedelta(hours=x)),
                (r'(\d+)\s*minutes?', lambda x: timedelta(minutes=x)),
                (r'(\d+)\s*mins?', lambda x: timedelta(minutes=x)),
                (r'(\d+)\s*hrs?', lambda x: timedelta(hours=x)),
                (r'(\d+)\s*hr', lambda x: timedelta(hours=x)),
                (r'(\d+)\s*min', lambda x: timedelta(minutes=x))
            ]
            
            for pattern, time_func in time_patterns:
                match = re.search(pattern, time_str)
                if match:
                    amount = int(match.group(1))
                    return now + time_func(amount)
            
            raise ValueError("Invalid time format. Use: in X hours/minutes/days/weeks")
        
        # Handle specific time today/tomorrow
        if ':' in time_str:
            # Check if it's just time (HH:MM) or date and time
            if len(time_str.split()) == 1:
                # Just time - assume today or tomorrow
                try:
                    time_parts = time_str.split(':')
                    if len(time_parts) == 2:
                        hour, minute = int(time_parts[0]), int(time_parts[1])
                        reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        
                        # If the time has already passed today, assume tomorrow
                        if reminder_time <= now:
                            reminder_time += timedelta(days=1)
                        
                        return reminder_time
                    else:
                        raise ValueError("Invalid time format. Use HH:MM")
                except ValueError:
                    raise ValueError("Invalid time format. Use HH:MM")
            else:
                # Date and time format
                try:
                    # Try various date formats
                    date_formats = [
                        "%Y-%m-%d %H:%M",
                        "%m/%d/%Y %H:%M",
                        "%d/%m/%Y %H:%M",
                        "%Y-%m-%d %H:%M:%S",
                        "%m/%d/%Y %H:%M:%S",
                        "%d/%m/%Y %H:%M:%S"
                    ]
                    
                    for fmt in date_formats:
                        try:
                            return datetime.strptime(time_str, fmt)
                        except ValueError:
                            continue
                    
                    raise ValueError("Invalid date/time format")
                except ValueError:
                    raise ValueError("Invalid date/time format")
        
        # Handle specific dates
        try:
            # Try date-only formats
            date_formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d/%m/%Y"
            ]
            
            for fmt in date_formats:
                try:
                    date_obj = datetime.strptime(time_str, fmt)
                    # Set to 9 AM on that date
                    return date_obj.replace(hour=9, minute=0, second=0, microsecond=0)
                except ValueError:
                    continue
            
            raise ValueError("Invalid date format")
        except ValueError:
            raise ValueError("Invalid time format")
    
    def _format_reminder_time(self, reminder_time: datetime) -> str:
        """Format reminder time for display"""
        now = datetime.now()
        time_diff = reminder_time - now
        
        if time_diff.total_seconds() <= 0:
            return f"**OVERDUE** ({reminder_time.strftime('%Y-%m-%d %H:%M')})"
        
        days = time_diff.days
        hours = int(time_diff.seconds // 3600)
        minutes = int((time_diff.seconds % 3600) // 60)
        
        if days > 0:
            return f"in {days} day(s), {hours}h {minutes}m ({reminder_time.strftime('%Y-%m-%d %H:%M')})"
        elif hours > 0:
            return f"in {hours}h {minutes}m ({reminder_time.strftime('%m-%d %H:%M')})"
        else:
            return f"in {minutes}m ({reminder_time.strftime('%H:%M')})"
    
    @commands.command(name='add', help='Add a new task to your to-do list')
    async def add_task(self, ctx, *, task_input: str):
        """Add a new task to the user's to-do list with optional deadline"""
        # Parse task and deadline
        deadline = None
        task = task_input
        
        # Check for deadline syntax: task | deadline
        if ' | ' in task_input:
            parts = task_input.split(' | ', 1)
            task = parts[0].strip()
            deadline_str = parts[1].strip()
            
            try:
                deadline = self._parse_deadline(deadline_str)
            except ValueError as e:
                await ctx.send(f"❌ {str(e)}")
                return
        
        if len(task) > MAX_TASK_LENGTH:
            await ctx.send(f"❌ Task is too long! Maximum {MAX_TASK_LENGTH} characters.")
            return
        
        user_id = str(ctx.author.id)
        success = self.db.add_task(user_id, task, deadline)
        
        if success:
            tasks = self.db.get_tasks(user_id)
            task_id = len(tasks)
            
            embed = discord.Embed(
                title="✅ Task Added!",
                description=f"**Task #{task_id}:** {task}",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            
            if deadline:
                status, time_remaining = self._get_deadline_status(deadline)
                embed.add_field(
                    name="⏰ Deadline",
                    value=f"{self._format_deadline(deadline)}\n{time_remaining}",
                    inline=True
                )
            
            embed.add_field(
                name="👤 User",
                value=f"<@{user_id}>",
                inline=True
            )
            
            embed.set_footer(text="Use !list to see your tasks")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Failed to add task. You may have reached the maximum number of tasks (50).")
    
    @commands.command(name='deadline', help='Set or update deadline for a task')
    async def set_deadline(self, ctx, task_id: int, *, deadline_str: str):
        """Set or update deadline for a task"""
        user_id = str(ctx.author.id)
        task = self.db.get_task(user_id, task_id)
        
        if not task:
            await ctx.send("❌ Task not found! Use `!list` to see your tasks.")
            return
        
        try:
            deadline = self._parse_deadline(deadline_str)
        except ValueError as e:
            await ctx.send(f"❌ {str(e)}")
            return
        
        # Update the task deadline
        task['deadline'] = deadline
        task['reminder_sent'] = False  # Reset reminder flag
        self.db._save_data()
        
        status, time_remaining = self._get_deadline_status(deadline)
        embed = discord.Embed(
            title="⏰ Deadline Updated!",
            description=f"**Task #{task_id}:** {task['task']}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name="New Deadline",
            value=f"{self._format_deadline(deadline)}\n{time_remaining}",
            inline=True
        )
        embed.set_footer(text=f"Updated by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    
    @commands.command(name='remindme', help='Set a custom reminder. Usage: !remindme <message> | <time>')
    async def remindme(self, ctx, *, reminder_input: str):
        """Set a custom reminder"""
        if ' | ' not in reminder_input:
            await ctx.send("❌ **Usage:** `!remindme <message> | <time>`\n\n**Examples:**\n• `!remindme Take medicine | in 2 hours`\n• `!remindme Call dentist | 14:30`\n• `!remindme Submit report | 2024-12-31 17:00`")
            return
        
        parts = reminder_input.split(' | ', 1)
        message = parts[0].strip()
        time_str = parts[1].strip()
        
        if not message:
            await ctx.send("❌ Please provide a reminder message!")
            return
        
        if len(message) > 200:
            await ctx.send("❌ Reminder message is too long! Maximum 200 characters.")
            return
        
        try:
            reminder_time = self._parse_reminder_time(time_str)
            
            # Check if reminder is in the past
            if reminder_time <= datetime.now():
                await ctx.send("❌ Reminder time must be in the future!")
                return
            
            # Check if reminder is too far in the future (more than 1 year)
            if reminder_time > datetime.now() + timedelta(days=365):
                await ctx.send("❌ Reminders cannot be set more than 1 year in advance!")
                return
            
            user_id = str(ctx.author.id)
            success = self.db.add_reminder(user_id, message, reminder_time.isoformat())
            
            if success:
                embed = discord.Embed(
                    title="⏰ Reminder Set!",
                    description=f"**Message:** {message}",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                
                embed.add_field(
                    name="⏰ Reminder Time",
                    value=self._format_reminder_time(reminder_time),
                    inline=False
                )
                
                embed.add_field(
                    name="📅 Exact Time",
                    value=reminder_time.strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True
                )
                
                embed.add_field(
                    name="👤 User",
                    value=f"<@{user_id}>",
                    inline=True
                )
                
                embed.set_footer(text="You'll receive a private message when the reminder is due!")
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to set reminder. You may have too many active reminders (max 20).")
                
        except ValueError as e:
            await ctx.send(f"❌ **Invalid time format:** {str(e)}\n\n**Valid formats:**\n• `in 2 hours`\n• `in 30 minutes`\n• `in 3 days`\n• `14:30` (today/tomorrow)\n• `2024-12-31 17:00`\n• `2024-12-31` (9 AM)")
    
    @commands.command(name='reminders', help='Show your active reminders')
    async def list_reminders(self, ctx):
        """List all active reminders for the user"""
        user_id = str(ctx.author.id)
        reminders = self.db.get_reminders(user_id)
        
        if not reminders:
            embed = discord.Embed(
                title="⏰ Your Reminders",
                description="You have no active reminders.",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(
                name="💡 Tip",
                value="Use `!remindme <message> | <time>` to set a reminder!",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="⏰ Your Active Reminders",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        for i, reminder in enumerate(reminders, 1):
            reminder_time = datetime.fromisoformat(reminder['reminder_time'])
            time_status = self._format_reminder_time(reminder_time)
            
            embed.add_field(
                name=f"🔔 Reminder #{reminder['id']}",
                value=f"**Message:** {reminder['message']}\n**Time:** {time_status}\n**Created:** {reminder['created_at'][:16]}",
                inline=False
            )
        
        embed.set_footer(text=f"You have {len(reminders)} active reminder(s)")
        await ctx.send(embed=embed)
    
    @commands.command(name='delreminder', help='Delete a reminder. Usage: !delreminder <id>')
    async def delete_reminder(self, ctx, reminder_id: int):
        """Delete a specific reminder"""
        user_id = str(ctx.author.id)
        success = self.db.delete_reminder(user_id, reminder_id)
        
        if success:
            embed = discord.Embed(
                title="✅ Reminder Deleted",
                description=f"Reminder #{reminder_id} has been deleted.",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Reminder not found or you don't have permission to delete it!")
    
    @commands.command(name='clearreminders', help='Delete all your reminders')
    async def clear_reminders(self, ctx):
        """Clear all reminders for the user"""
        user_id = str(ctx.author.id)
        count = self.db.clear_reminders(user_id)
        
        embed = discord.Embed(
            title="🗑️ Reminders Cleared",
            description=f"Deleted {count} reminder(s).",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        await ctx.send(embed=embed)

    @commands.command(name='list', help='Show your to-do list')
    async def list_tasks(self, ctx):
        """Show the user's to-do list"""
        user_id = str(ctx.author.id)
        tasks = self.db.get_tasks(user_id)
        
        if not tasks:
            embed = discord.Embed(
                title="📋 Your To-Do List",
                description="You have no tasks!",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(
                name="💡 Tip",
                value="Use `!add <task>` to add a new task!",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        # Separate completed and pending tasks
        pending_tasks = [task for task in tasks if not task['completed']]
        completed_tasks = [task for task in tasks if task['completed']]
        
        embed = discord.Embed(
            title="📋 Your To-Do List",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        # Add pending tasks
        if pending_tasks:
            pending_text = ""
            for task in pending_tasks:
                status = "⏳"
                task_text = f"{status} **#{task['id']}** {task['task']}"
                
                if task.get('deadline'):
                    deadline_status, time_remaining = self._get_deadline_status(task['deadline'])
                    if deadline_status == "overdue":
                        task_text += f" 🔴 (Overdue: {self._format_deadline(task['deadline'])})"
                    elif deadline_status == "urgent":
                        task_text += f" 🟡 (Due soon: {time_remaining})"
                    else:
                        task_text += f" ⏰ (Due: {time_remaining})"
                
                pending_text += task_text + "\n"
            
            embed.add_field(
                name=f"⏳ Pending Tasks ({len(pending_tasks)})",
                value=pending_text or "No pending tasks",
                inline=False
            )
        
        # Add completed tasks
        if completed_tasks:
            completed_text = ""
            for task in completed_tasks:
                status = "✅"
                completed_at = datetime.fromisoformat(task['completed_at']).strftime("%Y-%m-%d %H:%M")
                task_text = f"{status} **#{task['id']}** {task['task']} (Completed: {completed_at})"
                
                if task.get('deadline'):
                    task_text += f" ⏰ (Deadline: {self._format_deadline(task['deadline'])})"
                
                completed_text += task_text + "\n"
            
            embed.add_field(
                name=f"✅ Completed Tasks ({len(completed_tasks)})",
                value=completed_text or "No completed tasks",
                inline=False
            )
        
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    
    @commands.command(name='complete', help='Mark a task as completed. Usage: !complete <id>')
    async def complete_task(self, ctx, task_id: int):
        """Mark a task as completed"""
        user_id = str(ctx.author.id)
        task = self.db.get_task(user_id, task_id)
        
        if not task:
            await ctx.send("❌ Task not found! Use `!list` to see your tasks.")
            return
        
        if task['completed']:
            await ctx.send("❌ This task is already completed!")
            return
        
        success = self.db.complete_task(user_id, task_id)
        
        if success:
            embed = discord.Embed(
                title="✅ Task Completed!",
                description=f"**Task #{task_id}:** {task['task']}",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            
            if task.get('deadline'):
                embed.add_field(
                    name="⏰ Original Deadline",
                    value=self._format_deadline(task['deadline']),
                    inline=True
                )
            
            embed.set_footer(text=f"Completed by {ctx.author.display_name}")
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Failed to complete task. Please try again.")
    
    @commands.command(name='uncomplete', help='Mark a task as uncompleted. Usage: !uncomplete <id>')
    async def uncomplete_task(self, ctx, task_id: int):
        """Mark a completed task as uncompleted"""
        user_id = str(ctx.author.id)
        task = self.db.get_task(user_id, task_id)
        
        if not task:
            await ctx.send("❌ Task not found! Use `!list` to see your tasks.")
            return
        
        if not task['completed']:
            await ctx.send("❌ This task is not completed!")
            return
        
        success = self.db.uncomplete_task(user_id, task_id)
        
        if success:
            embed = discord.Embed(
                title="⏳ Task Uncompleted!",
                description=f"**Task #{task_id}:** {task['task']}",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Uncompleted by {ctx.author.display_name}")
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Failed to uncomplete task. Please try again.")
    
    @commands.command(name='remove', help='Remove a task. Usage: !remove <id>')
    async def remove_task(self, ctx, task_id: int):
        """Remove a task from the list"""
        user_id = str(ctx.author.id)
        task = self.db.get_task(user_id, task_id)
        
        if not task:
            await ctx.send("❌ Task not found! Use `!list` to see your tasks.")
            return
        
        success = self.db.remove_task(user_id, task_id)
        
        if success:
            embed = discord.Embed(
                title="🗑️ Task Removed!",
                description=f"**Task #{task_id}:** {task['task']}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Removed by {ctx.author.display_name}")
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Failed to remove task. Please try again.")
    
    @commands.command(name='clear', help='Remove all completed tasks')
    async def clear_completed(self, ctx):
        """Remove all completed tasks"""
        user_id = str(ctx.author.id)
        count = self.db.clear_completed_tasks(user_id)
        
        embed = discord.Embed(
            title="🧹 Completed Tasks Cleared!",
            description=f"Removed {count} completed task(s).",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Cleared by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    
    @commands.command(name='clearall', help='Remove all tasks')
    async def clear_all(self, ctx):
        """Remove all tasks"""
        user_id = str(ctx.author.id)
        count = self.db.clear_all_tasks(user_id)
        
        embed = discord.Embed(
            title="🗑️ All Tasks Cleared!",
            description=f"Removed {count} task(s).",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Cleared by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    
    @commands.command(name='help', help='Show help information')
    async def help_command(self, ctx):
        """Show help information"""
        embed = discord.Embed(
            title="🤖 To-Do Bot Help",
            description="Welcome to your personal to-do list manager!",
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
            name="⏰ Time Formats",
            value=(
                "**Deadlines:** `in 2 hours`, `2024-12-31 17:00`\n"
                "**Reminders:** `in 30 minutes`, `14:30`, `2024-12-31`\n"
                "**Both support:** relative time, specific dates/times"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔒 Privacy Features",
            value=(
                "• **Private to-do lists** - Only you can see your tasks\n"
                "• **Encrypted storage** - All data is encrypted\n"
                "• **Data hashing** - User IDs and content are hashed\n"
                "• **Private reminders** - Reminders sent via DM only"
            ),
            inline=False
        )
        
        embed.set_footer(text="Your data is encrypted and private - only you can see your tasks and reminders!")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TodoCommands(bot)) 