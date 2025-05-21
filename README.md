# Discord Gambling Bot Dashboard

## Overview

A Discord bot with gambling features and a real-time web dashboard. The bot connects to Discord servers, processes commands, and allows users to play gambling mini-games. The dashboard provides real-time monitoring of the bot's status, user statistics, and a leaderboard.

## System Architecture

- **Backend:** Python, Flask, Flask-SocketIO, Flask-SQLAlchemy, discord.py
- **Frontend:** Jinja2 templates, Bootstrap (dark theme), Socket.IO client, Font Awesome
- **Database:** SQLite (dev), PostgreSQL (prod-ready)

## Key Components

- `app.py`: Flask app, SocketIO, dashboard routes, API
- `bot.py`: Discord bot, commands, event handling
- `gambling.py`: Gambling logic
- `models.py`: SQLAlchemy models
- Templates: `base.html`, `index.html`, `dashboard.html`, `leaderboard.html`

## Data Flow

1. User triggers a Discord command
2. Bot processes and updates the database
3. Real-time updates sent to dashboard via SocketIO

## Python Dependencies

- flask
- flask-socketio
- flask-sqlalchemy
- psycopg2
- discord.py
- python-dotenv

## Deployment

- Python 3.11
- SQLite (dev) / PostgreSQL (prod)
- Gunicorn for production
- Entry point: `main:app`
- Port: 5000

Secrets and tokens are managed via environment variables.