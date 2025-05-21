import random
from datetime import datetime, timedelta

def process_game(amount, current_multiplier=1.0):
    """
    Process a gambling game and return the result.

    The user's current multiplier (affected by console focus streak)
    increases their win chance and potential winnings.

    Args:
        amount (int): The amount of coins being gambled
        current_multiplier (float): The user's current multiplier (from console focus streak)

    Returns:
        tuple: (result, won, multiplier)
            - result (int): Amount won or lost
            - won (bool): Whether the user won
            - multiplier (float): The multiplier used for this game
    """
    # Base win chance is 45%
    win_chance = 45
    
    # Apply multiplier (can't go above 65% win chance)
    adjusted_win_chance = min(65, win_chance + (current_multiplier - 1) * 12)
    
    # Determine if user won
    won = random.randint(1, 100) <= adjusted_win_chance
    
    if won:
        # Chance for a "jackpot" win (5% chance)
        if random.random() < 0.05:
            jackpot_multiplier = random.uniform(5, 15)
            total_win = int(amount * jackpot_multiplier)
            return total_win, True, jackpot_multiplier
        # Win calculation with higher multiplier range
        base_win = amount
        multiplier_bonus = random.uniform(1.2, 3.5) * current_multiplier
        total_win = int(base_win * multiplier_bonus)
        
        # Apply some randomization
        total_win = int(total_win * random.uniform(0.95, 1.15))
        
        # Ensure minimum win
        total_win = max(1, total_win)
        
        return total_win, True, multiplier_bonus
    else:
        # Loss is just the amount gambled
        return amount, False, current_multiplier

def calculate_multiplier(console_focus_streak):
    """
    Calculate multiplier based on console focus streak.

    Each consecutive play in a #console or #bot-console channel
    increases the user's multiplier by 0.10, up to a max of 3.0x.

    Args:
        console_focus_streak (int): Number of consecutive plays in console channels

    Returns:
        float: The calculated multiplier
    """
    # Base multiplier is 1.0
    # Each consecutive console interaction adds 0.10 up to a maximum of 3.0
    base_multiplier = 1.0
    streak_bonus = min(2.0, console_focus_streak * 0.10)
    
    return base_multiplier + streak_bonus
