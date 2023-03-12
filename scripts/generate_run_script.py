import sys
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


if __name__ == "__main__":
    generate_run_script()
    print("已生成 run.sh")
