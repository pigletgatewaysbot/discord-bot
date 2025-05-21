from app import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(64), unique=True, nullable=False)
    username = db.Column(db.String(64), nullable=False)
    avatar_url = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    gambling_stats = db.relationship("GamblingStats", backref="user", lazy=True, uselist=False)
    
    def __repr__(self):
        return f"<User {self.username}>"

class GamblingStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    coins = db.Column(db.Integer, default=100)
    games_played = db.Column(db.Integer, default=0)
    games_won = db.Column(db.Integer, default=0)
    games_lost = db.Column(db.Integer, default=0)
    highest_win = db.Column(db.Integer, default=0)
    highest_loss = db.Column(db.Integer, default=0)
    total_winnings = db.Column(db.Integer, default=0)
    multiplier = db.Column(db.Float, default=1.0)  # Console focus multiplier
    last_multiplier_update = db.Column(db.DateTime, default=datetime.utcnow)
    console_focus_streak = db.Column(db.Integer, default=0)  # Consecutive plays in console channels
    
    def __repr__(self):
        return f"<GamblingStats for {self.user.username}>"
