import os
import logging
import asyncio
import threading
import json
import random
from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ext import commands, tasks
from collections import deque

from app import db, bot_status
from models import User, GamblingStats
from gambling import process_game, calculate_multiplier

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure the Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Socket.IO instance (will be set by the app)
socketio = None

# Queue for bot events
event_queue = deque(maxlen=10)
command_queue = []
command_responses = {}

# Commands implementation
@tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    bot_status["commands_used"] += 1
    event_queue.append({
        "type": "command",
        "command": "ping",
        "user": interaction.user.name,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })
    
    # Emit event via socket.io
    if socketio:
        socketio.emit("bot_event", {
            "type": "command_used",
            "command": "ping",
            "user": interaction.user.name
        })
    
    await interaction.response.send_message(f"Pong! Latency: {round(bot.latency * 1000)}ms")

@tree.command(name="gamble", description="Gamble your coins with a chance to win or lose")
@app_commands.describe(amount="Amount of coins to gamble")
async def gamble(interaction: discord.Interaction, amount: int):
    bot_status["commands_used"] += 1
    bot_status["gambling_sessions"] += 1
    
    event_queue.append({
        "type": "command",
        "command": "gamble",
        "user": interaction.user.name,
        "amount": amount,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })
    
    # Get or create user
    with db.session() as session:
        user = session.query(User).filter_by(discord_id=str(interaction.user.id)).first()
        if not user:
            user = User(
                discord_id=str(interaction.user.id),
                username=interaction.user.name,
                avatar_url=str(interaction.user.avatar.url) if interaction.user.avatar else None
            )
            session.add(user)
            session.commit()
            
            # Create gambling stats
            gambling_stats = GamblingStats(user_id=user.id)
            session.add(gambling_stats)
            session.commit()
        else:
            gambling_stats = user.gambling_stats
            
        # Check if user has enough coins
        if gambling_stats.coins < amount:
            await interaction.response.send_message(f"You don't have enough coins! You only have {gambling_stats.coins} coins.")
            return
        
        # Process the game
        result, won, multiplier = process_game(amount, gambling_stats.multiplier)

        # Update stats
        gambling_stats.games_played += 1

        if won:
            gambling_stats.games_won += 1
            gambling_stats.coins += result
            gambling_stats.total_winnings += result
            gambling_stats.highest_win = max(gambling_stats.highest_win, result)
            # Big win/jackpot message
            if multiplier >= 5:
                message = f"💰 JACKPOT! You won {result} coins with a {multiplier:.2f}x multiplier! Casino legend! Your balance: {gambling_stats.coins} coins."
            elif multiplier >= 3:
                message = f"🎲 BIG WIN! {result} coins with a {multiplier:.2f}x multiplier! Your balance: {gambling_stats.coins} coins."
            elif multiplier >= 2:
                message = f"✨ Nice! You won {result} coins ({multiplier:.2f}x). Balance: {gambling_stats.coins} coins."
            else:
                message = f"🎉 You won {result} coins! Your current balance is {gambling_stats.coins} coins. (Multiplier: {multiplier:.2f}x)"
        else:
            gambling_stats.games_lost += 1
            gambling_stats.coins -= amount
            gambling_stats.total_winnings -= amount
            gambling_stats.highest_loss = max(gambling_stats.highest_loss, amount)
            message = f"😭 You lost {amount} coins! Your current balance is {gambling_stats.coins} coins. (Multiplier: {multiplier:.2f}x)"

        # Add focus streak/multiplier info to the message
        message += f"\n\n🎮 Console Focus Streak: {gambling_stats.console_focus_streak} | Multiplier: {gambling_stats.multiplier:.2f}x\n" \
                   f"Play in #console or #bot-console channels to increase your multiplier!"

        session.commit()
        
        # Emit event via socket.io
        if socketio:
            socketio.emit("bot_event", {
                "type": "gambling_result",
                "user": interaction.user.name,
                "amount": amount,
                "result": "win" if won else "loss",
                "coins": gambling_stats.coins
            })
        
        await interaction.response.send_message(message)

@tree.command(name="stats", description="View your gambling statistics")
async def stats(interaction: discord.Interaction):
    bot_status["commands_used"] += 1
    
    event_queue.append({
        "type": "command",
        "command": "stats",
        "user": interaction.user.name,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })
    
    # Get user stats
    with db.session() as session:
        user = session.query(User).filter_by(discord_id=str(interaction.user.id)).first()
        if not user or not user.gambling_stats:
            await interaction.response.send_message("You haven't gambled yet! Use the `/gamble` command to start.")
            return
        
        stats = user.gambling_stats
        
        # Create embed
        embed = discord.Embed(
            title=f"{interaction.user.name}'s Gambling Stats",
            color=discord.Color.blue()
        )
        
        # Add fields
        embed.add_field(name="Balance", value=f"{stats.coins} coins", inline=True)
        embed.add_field(name="Games Played", value=str(stats.games_played), inline=True)
        embed.add_field(name="Win Rate", value=f"{(stats.games_won / stats.games_played * 100) if stats.games_played > 0 else 0:.1f}%", inline=True)
        embed.add_field(name="Highest Win", value=f"{stats.highest_win} coins", inline=True)
        embed.add_field(name="Highest Loss", value=f"{stats.highest_loss} coins", inline=True)
        embed.add_field(name="Net Winnings", value=f"{stats.total_winnings} coins", inline=True)
        embed.add_field(name="Current Multiplier", value=f"{stats.multiplier:.2f}x", inline=True)
        embed.add_field(name="Console Focus Streak", value=f"{stats.console_focus_streak} plays", inline=True)
        
        # Add footer
        embed.set_footer(text="Keep gambling to increase your multiplier!")
        
        await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    logger.info(f"Bot is ready as {bot.user.name}")
    bot_status["connected"] = True
    bot_status["start_time"] = datetime.now()
    bot_status["guilds"] = len(bot.guilds)
    
    # Register slash commands
    try:
        synced = await tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
    
    # Start background tasks
    update_status.start()
    check_command_queue.start()
    
    if socketio:
        socketio.emit("bot_status_update", {
            "status": "connected",
            "username": bot.user.name,
            "guilds": len(bot.guilds)
        })

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Update active users count
    bot_status["active_users"] = len(set([m.id for m in bot.get_all_members()]))
    
    # Check for console focus multiplier
    if message.channel.name == "console" or message.channel.name == "bot-console":
        # Update the user's console focus multiplier
        with db.session() as session:
            user = session.query(User).filter_by(discord_id=str(message.author.id)).first()
            if user and user.gambling_stats:
                # Increment streak and recalculate multiplier
                user.gambling_stats.console_focus_streak += 1
                user.gambling_stats.multiplier = calculate_multiplier(user.gambling_stats.console_focus_streak)
                session.commit()
    else:
        # Reset streak if user plays outside console channels
        with db.session() as session:
            user = session.query(User).filter_by(discord_id=str(message.author.id)).first()
            if user and user.gambling_stats and user.gambling_stats.console_focus_streak > 0:
                user.gambling_stats.console_focus_streak = 0
                user.gambling_stats.multiplier = calculate_multiplier(0)
                session.commit()
    
    # Update bot status events
    event_queue.append({
        "type": "message",
        "user": message.author.name,
        "channel": message.channel.name,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })
    
    bot_status["latest_events"] = list(event_queue)
    
    # Process commands
    await bot.process_commands(message)

@tasks.loop(seconds=5)
async def update_status():
    # Update bot status
    bot_status["guilds"] = len(bot.guilds)
    bot_status["active_users"] = len(set([m.id for m in bot.get_all_members()]))
    bot_status["latest_events"] = list(event_queue)
    
    if socketio:
        # Convert to JSON-safe format using the app's CustomJSONEncoder
        from app import CustomJSONEncoder
        import json
        serialized_status = json.loads(json.dumps(bot_status, cls=CustomJSONEncoder))
        socketio.emit("status_update", serialized_status)

@tasks.loop(seconds=1)
async def check_command_queue():
    global command_queue
    
    if command_queue:
        command_id, command_text = command_queue.pop(0)
        try:
            # Process manual command from web interface
            if command_text.startswith("/"):
                # Simulate slash command
                command_name = command_text[1:].split(" ")[0]
                response = f"Executed slash command: {command_name}"
            else:
                # Regular command
                response = f"Executed command: {command_text}"
                
            # Store response
            command_responses[command_id] = {
                "success": True,
                "response": response
            }
            
        except Exception as e:
            command_responses[command_id] = {
                "success": False,
                "response": str(e)
            }

def start_bot(socketio_instance=None):
    global socketio
    socketio = socketio_instance
    
    # Get token from environment variable
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("No Discord token found in environment variables!")
        return
    
    # Run the bot
    try:
        bot.run(token)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        bot_status["connected"] = False
        if socketio:
            socketio.emit("bot_status_update", {
                "status": "disconnected",
                "error": str(e)
            })

def send_bot_command(command):
    command_id = random.randint(1000, 9999)
    command_queue.append((command_id, command))
    
    # Wait for response (max 5 seconds)
    start_time = datetime.now()
    while command_id not in command_responses and (datetime.now() - start_time).total_seconds() < 5:
        import time
        time.sleep(0.1)
    
    if command_id in command_responses:
        response = command_responses.pop(command_id)
        return response
    else:
        return {"success": False, "response": "Command timed out"}
