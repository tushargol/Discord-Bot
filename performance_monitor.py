import time
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor bot performance metrics"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.command_times = {}
        self.db_operations = {}
        self.reminder_checks = []
        self.memory_usage = []
        self.cpu_usage = []
        
    def record_command(self, command_name: str, execution_time: float):
        """Record command execution time"""
        if command_name not in self.command_times:
            self.command_times[command_name] = []
        self.command_times[command_name].append(execution_time)
        
        # Keep only last 100 entries per command
        if len(self.command_times[command_name]) > 100:
            self.command_times[command_name] = self.command_times[command_name][-100:]
    
    def record_db_operation(self, operation: str, execution_time: float):
        """Record database operation time"""
        if operation not in self.db_operations:
            self.db_operations[operation] = []
        self.db_operations[operation].append(execution_time)
        
        # Keep only last 50 entries per operation
        if len(self.db_operations[operation]) > 50:
            self.db_operations[operation] = self.db_operations[operation][-50:]
    
    def record_reminder_check(self, reminders_sent: int, deadlines_sent: int, execution_time: float):
        """Record reminder check performance"""
        self.reminder_checks.append({
            'timestamp': datetime.now(),
            'reminders_sent': reminders_sent,
            'deadlines_sent': deadlines_sent,
            'execution_time': execution_time
        })
        
        # Keep only last 100 entries
        if len(self.reminder_checks) > 100:
            self.reminder_checks = self.reminder_checks[-100:]
    
    def record_system_metrics(self):
        """Record current system metrics"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            self.memory_usage.append({
                'timestamp': datetime.now(),
                'rss': memory_info.rss,  # Resident Set Size in bytes
                'vms': memory_info.vms,  # Virtual Memory Size in bytes
                'cpu_percent': cpu_percent
            })
            
            # Keep only last 100 entries
            if len(self.memory_usage) > 100:
                self.memory_usage = self.memory_usage[-100:]
                
        except Exception as e:
            logger.warning(f"Failed to record system metrics: {e}")
    
    def get_performance_summary(self) -> Dict:
        """Get a summary of performance metrics"""
        uptime = datetime.now() - self.start_time
        
        # Calculate command performance
        command_stats = {}
        for cmd, times in self.command_times.items():
            if times:
                command_stats[cmd] = {
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'total_calls': len(times)
                }
        
        # Calculate database performance
        db_stats = {}
        for op, times in self.db_operations.items():
            if times:
                db_stats[op] = {
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'total_operations': len(times)
                }
        
        # Calculate reminder check performance
        reminder_stats = {}
        if self.reminder_checks:
            recent_checks = self.reminder_checks[-10:]  # Last 10 checks
            avg_execution_time = sum(check['execution_time'] for check in recent_checks) / len(recent_checks)
            total_reminders_sent = sum(check['reminders_sent'] for check in recent_checks)
            total_deadlines_sent = sum(check['deadlines_sent'] for check in recent_checks)
            
            reminder_stats = {
                'avg_execution_time': avg_execution_time,
                'total_reminders_sent': total_reminders_sent,
                'total_deadlines_sent': total_deadlines_sent,
                'checks_recorded': len(self.reminder_checks)
            }
        
        # Calculate system metrics
        system_stats = {}
        if self.memory_usage:
            recent_memory = self.memory_usage[-10:]  # Last 10 measurements
            avg_memory_mb = sum(usage['rss'] for usage in recent_memory) / len(recent_memory) / 1024 / 1024
            avg_cpu = sum(usage['cpu_percent'] for usage in recent_memory) / len(recent_memory)
            
            system_stats = {
                'avg_memory_mb': avg_memory_mb,
                'avg_cpu_percent': avg_cpu,
                'current_memory_mb': self.memory_usage[-1]['rss'] / 1024 / 1024 if self.memory_usage else 0,
                'current_cpu_percent': self.memory_usage[-1]['cpu_percent'] if self.memory_usage else 0
            }
        
        return {
            'uptime_seconds': uptime.total_seconds(),
            'uptime_formatted': str(uptime).split('.')[0],  # Remove microseconds
            'command_stats': command_stats,
            'db_stats': db_stats,
            'reminder_stats': reminder_stats,
            'system_stats': system_stats,
            'total_commands': sum(len(times) for times in self.command_times.values()),
            'total_db_operations': sum(len(times) for times in self.db_operations.values())
        }
    
    def get_performance_embed(self) -> Optional[Dict]:
        """Get performance metrics as a Discord embed"""
        try:
            summary = self.get_performance_summary()
            
            embed = {
                'title': '📊 Bot Performance Metrics',
                'color': 0x00ff00,  # Green
                'timestamp': datetime.now().isoformat(),
                'fields': []
            }
            
            # Uptime
            embed['fields'].append({
                'name': '⏰ Uptime',
                'value': summary['uptime_formatted'],
                'inline': True
            })
            
            # System metrics
            if summary['system_stats']:
                sys_stats = summary['system_stats']
                embed['fields'].append({
                    'name': '💻 System',
                    'value': f"Memory: {sys_stats['avg_memory_mb']:.1f}MB\nCPU: {sys_stats['avg_cpu_percent']:.1f}%",
                    'inline': True
                })
            
            # Command performance
            if summary['command_stats']:
                cmd_text = ""
                for cmd, stats in list(summary['command_stats'].items())[:5]:  # Top 5 commands
                    cmd_text += f"`{cmd}`: {stats['avg_time']:.3f}s avg\n"
                
                if cmd_text:
                    embed['fields'].append({
                        'name': '⚡ Command Performance',
                        'value': cmd_text,
                        'inline': False
                    })
            
            # Database performance
            if summary['db_stats']:
                db_text = ""
                for op, stats in list(summary['db_stats'].items())[:3]:  # Top 3 operations
                    db_text += f"`{op}`: {stats['avg_time']:.3f}s avg\n"
                
                if db_text:
                    embed['fields'].append({
                        'name': '🗄️ Database Performance',
                        'value': db_text,
                        'inline': False
                    })
            
            # Reminder performance
            if summary['reminder_stats']:
                rem_stats = summary['reminder_stats']
                embed['fields'].append({
                    'name': '🔔 Reminder Performance',
                    'value': f"Avg check time: {rem_stats['avg_execution_time']:.3f}s\nReminders sent: {rem_stats['total_reminders_sent']}\nDeadlines sent: {rem_stats['total_deadlines_sent']}",
                    'inline': True
                })
            
            # Totals
            embed['fields'].append({
                'name': '📈 Totals',
                'value': f"Commands: {summary['total_commands']}\nDB Operations: {summary['total_db_operations']}",
                'inline': True
            })
            
            embed['footer'] = {'text': 'Performance monitoring active'}
            
            return embed
            
        except Exception as e:
            logger.error(f"Failed to create performance embed: {e}")
            return None
    
    def clear_old_data(self):
        """Clear old performance data to prevent memory bloat"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # Clear old reminder checks
        self.reminder_checks = [
            check for check in self.reminder_checks 
            if check['timestamp'] > cutoff_time
        ]
        
        # Clear old system metrics
        self.memory_usage = [
            usage for usage in self.memory_usage 
            if usage['timestamp'] > cutoff_time
        ]
        
        # Clear old command times (keep only last 50 per command)
        for cmd in self.command_times:
            if len(self.command_times[cmd]) > 50:
                self.command_times[cmd] = self.command_times[cmd][-50:]
        
        # Clear old db operations (keep only last 25 per operation)
        for op in self.db_operations:
            if len(self.db_operations[op]) > 25:
                self.db_operations[op] = self.db_operations[op][-25:]

# Global performance monitor instance
performance_monitor = PerformanceMonitor() 