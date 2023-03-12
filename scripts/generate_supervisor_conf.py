import sys
import getpass
from pathlib import Path


def generate_run_script() -> None:
    path = Path(__file__).parent.parent / "run.sh"
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            f"""
#!/bin/bash
source {Path(sys.executable).parent / "activate"}
{Path(sys.executable).parent / "nb"} datastore upgrade
{Path(sys.executable).parent / "nb"} run
""".strip()
        )


def generate_supervisor_config():
    path = Path(__file__).parent
    if not (path.parent / "run.sh").exists():
        generate_run_script()
    with open(path / "migangbot.conf", "w", encoding="utf-8") as f:
        f.write(
            f"""
[program:migangbot]
command=/bin/bash {path.parent.resolve() / "run.sh"}
numprocs=1
process_name=migangbot
directory={path.parent.resolve()}
user = {getpass.getuser()}
autostart = true
autorestart = true
stopasgroup = true
killasgroup = true
stdout_logfile=/var/log/supervisor/migangbot.out
stderr_logfile=/var/log/supervisor/migangbot.err""".strip()
        )


if __name__ == "__main__":
    generate_supervisor_config()
