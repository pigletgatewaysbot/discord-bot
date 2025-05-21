import os
import logging
import threading
import json
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Custom JSON encoder to handle datetime objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

# Create the database base class
class Base(DeclarativeBase):
    pass

# Initialize the app and database
db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_dev")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Create database directory if it doesn't exist
db_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database')
os.makedirs(db_dir, exist_ok=True)

# Configure SQLAlchemy with absolute path
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(db_dir, "bot.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with the app
db.init_app(app)

# Initialize SocketIO with custom JSON encoder
socketio = SocketIO(app, cors_allowed_origins="*", json=json, json_encoder=CustomJSONEncoder)

# Import models and create tables
with app.app_context():
    from models import User, GamblingStats
    db.create_all()

# Global variables for bot status
bot_status = {
    "connected": False,
    "uptime": 0,
    "start_time": None,
    "guilds": 0,
    "commands_used": 0,
    "gambling_sessions": 0,
    "active_users": 0,
    "latest_events": []
}

# Import and initialize bot in a separate thread
from bot import start_bot, send_bot_command

def run_discord_bot():
    logger.info("Starting Discord bot in a separate thread...")
    start_bot(socketio)

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    with app.app_context():
        # Get top gamblers for leaderboard
        top_gamblers = GamblingStats.query.order_by(GamblingStats.total_winnings.desc()).limit(10).all()
        return render_template("dashboard.html", bot_status=bot_status, top_gamblers=top_gamblers)

@app.route("/leaderboard")
def leaderboard():
    with app.app_context():
        top_gamblers = GamblingStats.query.order_by(GamblingStats.total_winnings.desc()).limit(20).all()
        return render_template("leaderboard.html", top_gamblers=top_gamblers)

@app.route("/api/bot/status")
def get_bot_status():
    if bot_status["start_time"]:
        bot_status["uptime"] = (datetime.now() - bot_status["start_time"]).total_seconds()
    # Use the custom JSON encoder to properly handle datetime objects
    return jsonify(json.loads(json.dumps(bot_status, cls=CustomJSONEncoder)))

@app.route("/api/bot/command", methods=["POST"])
def send_command():
    if not request.json:
        return jsonify({"error": "Invalid JSON data"}), 400
        
    command = request.json.get("command")
    if not command:
        return jsonify({"error": "No command provided"}), 400
    
    try:
        response = send_bot_command(command)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        return jsonify({"error": str(e)}), 500

# SocketIO events
@socketio.on("connect")
def handle_connect(auth=None):
    logger.info("Client connected to SocketIO")
    # Use the custom JSON encoder to properly handle datetime objects
    serialized_status = json.loads(json.dumps(bot_status, cls=CustomJSONEncoder))
    emit("status_update", serialized_status)

@socketio.on("request_status")
def handle_request_status():
    # Use the custom JSON encoder to properly handle datetime objects
    serialized_status = json.loads(json.dumps(bot_status, cls=CustomJSONEncoder))
    emit("status_update", serialized_status)

# Start the bot in a separate thread when the application starts
bot_thread = threading.Thread(target=run_discord_bot)
bot_thread.daemon = True
bot_thread.start()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=True, log_output=True)
