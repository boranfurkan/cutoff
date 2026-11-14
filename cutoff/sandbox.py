"""Docker sandbox: one container per run, with the repo checkout mounted at /work."""
import subprocess
import uuid
from pathlib import Path

from .config import SANDBOX_IMAGE


class Sandbox:
    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir.resolve()
        self.name = f"cutoff-{uuid.uuid4().hex[:10]}"

    def __enter__(self):
        subprocess.run(
            ["docker", "run", "-d", "--rm", "--name", self.name, "--memory", "2g", "--cpus", "2",
             "-v", f"{self.repo_dir}:/work", "-v", "cutoff-pip-cache:/root/.cache/pip",
             "-w", "/work", "-e", "PYTHONDONTWRITEBYTECODE=1", SANDBOX_IMAGE, "sleep", "3600"],
            check=True, capture_output=True, text=True,
        )
        return self

    def __exit__(self, *exc):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)

    def run(self, command: str, timeout: int = 300) -> tuple[int, str]:
        """Run a shell command in the container. Returns (exit code, combined output)."""
        try:
            p = subprocess.run(["docker", "exec", self.name, "sh", "-c", command],
                               capture_output=True, text=True, timeout=timeout)
            return p.returncode, (p.stdout + p.stderr)
        except subprocess.TimeoutExpired:
            return 124, f"command timed out after {timeout}s"
