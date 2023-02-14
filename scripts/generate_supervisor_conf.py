import sys
import getpass
from pathlib import Path


def generate_supervisor_config():
    path = Path(__file__).parent
    with open(path / "migangbot.conf", "w", encoding="utf-8") as f:
        f.write(
            f"""
[program:migangbot]
command={sys.executable} bot.py
numprocs=1
process_name=migangbot
directory={path.parent.resolve()}
user = {getpass.getuser()}
autostart = true
autorestart = true
stdout_logfile=/var/log/supervisor/migangbot.out
stderr_logfile=/var/log/supervisor/migangbot.err""".strip()
        )

if __name__ == "__main__":
    generate_supervisor_config()