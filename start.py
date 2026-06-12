"""
start.py  –  Single entry point for Render deployment.
Starts Flask (Gunicorn) and the Discord bot in parallel threads.
"""

import threading
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("start")


def run_flask():
    from config import PORT, DEBUG
    if DEBUG:
        from app import app
        app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
    else:
        import subprocess
        workers = os.environ.get("GUNICORN_WORKERS", "2")
        cmd = [
            sys.executable, "-m", "gunicorn",
            "app:app",
            "--bind", f"0.0.0.0:{PORT}",
            "--workers", workers,
            "--timeout", "120",
            "--log-level", "info",
            "--access-logfile", "-",
        ]
        import subprocess
        subprocess.run(cmd)


def run_bot():
    try:
        from bot import run_bot as _run
        _run()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")


if __name__ == "__main__":
    logger.info("Starting FreeFire Hub platform...")

    flask_thread = threading.Thread(target=run_flask, daemon=True, name="Flask")
    bot_thread   = threading.Thread(target=run_bot,   daemon=True, name="Bot")

    flask_thread.start()
    bot_thread.start()

    logger.info("Both services started. Waiting...")

    try:
        flask_thread.join()
        bot_thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
        sys.exit(0)
