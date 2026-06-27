"""
main.py - بات جنگ جهانی دوم - همیشه در حال اجرا
"""
import time
import logging
import subprocess
import sys
import os
import threading
from flask import Flask

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  Keep-Alive Web Server (برای Replit)
# ─────────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "🤖 WW2 Bot is alive!", 200

@flask_app.route("/health")
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)

def start_keep_alive():
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    logger.info("✅ Keep-alive server started")

# ─────────────────────────────────────────────
#  Bot Runner - هرگز متوقف نمی‌شود
# ─────────────────────────────────────────────
def run_bot():
    start_keep_alive()

    restart_count = 0
    wait_time     = 3   # ثانیه انتظار بین ری‌استارت‌ها

    logger.info("🚀 Starting WW2 Bot...")

    while True:
        try:
            logger.info(f"▶️  Starting bot (attempt #{restart_count + 1})...")
            result = subprocess.run(
                [sys.executable, "bot.py"],
                check=False
            )
            exit_code = result.returncode
            restart_count += 1

            if exit_code == 0:
                logger.info("✅ Bot exited cleanly. Restarting...")
                wait_time = 3
            else:
                logger.warning(f"⚠️  Bot crashed (exit code: {exit_code}). Restarting in {wait_time}s...")
                # اگر بات سریع crash کرد، کمی صبر می‌کنیم
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, 30)  # حداکثر 30 ثانیه

        except KeyboardInterrupt:
            logger.info("🛑 Stopped by user.")
            break
        except Exception as e:
            logger.error(f"❌ Runner error: {e}. Restarting in {wait_time}s...")
            time.sleep(wait_time)
            wait_time = min(wait_time * 2, 30)

if __name__ == "__main__":
    run_bot()
