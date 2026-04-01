"""
Seeding worker — Background job manager for running seed-copilot in the web UI.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SeedingJobStatus(str, Enum):
    """Status of a seeding job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SeedingJobResult:
    """Result of a single seeding iteration."""
    project_title: str
    facts_created: int
    elements_created: int
    convergence_score: float


@dataclass
class SeedingJob:
    """Represents a seeding job."""
    job_id: str
    count: int
    status: SeedingJobStatus = SeedingJobStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_iteration: int = 0
    results: list[SeedingJobResult] = None
    error_message: Optional[str] = None
    output: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.results is None:
            self.results = []

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        data["started_at"] = self.started_at.isoformat() if self.started_at else None
        data["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        data["status"] = self.status.value
        data["results"] = [asdict(r) for r in self.results]
        return data


class SeededingJobManager:
    """Manages background seeding jobs."""

    def __init__(self):
        """Initialize job manager."""
        self._jobs: dict[str, SeedingJob] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        self._stop_flags: dict[str, threading.Event] = {}
        self._job_counter = 0

    def create_job(self, count: int) -> SeedingJob:
        """Create a new seeding job."""
        with self._lock:
            self._job_counter += 1
            job_id = f"job-{self._job_counter:04d}"
            job = SeedingJob(job_id=job_id, count=count)
            self._jobs[job_id] = job
            self._stop_flags[job_id] = threading.Event()
            return job

    def start_job(self, job_id: str) -> bool:
        """Start a seeding job in the background."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status != SeedingJobStatus.PENDING:
                return False

            job.status = SeedingJobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)

        # Start background thread
        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()
        self._threads[job_id] = thread
        return True

    def stop_job(self, job_id: str) -> bool:
        """Request a job to stop."""
        if job_id not in self._stop_flags:
            return False
        self._stop_flags[job_id].set()
        return True

    def get_job(self, job_id: str) -> Optional[SeedingJob]:
        """Get a job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def get_all_jobs(self) -> list[SeedingJob]:
        """Get all jobs, sorted by creation time (most recent first)."""
        with self._lock:
            jobs = list(self._jobs.values())
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def _run_job(self, job_id: str):
        """Run a seeding job (executed in background thread)."""
        job = self.get_job(job_id)
        if job is None:
            return

        try:
            # Build command
            cmd = [
                ".venv\\Scripts\\python.exe",
                "-m", "factdb", "seed-copilot",
                "--count", str(job.count),
                "--verbose"
            ]

            # Run subprocess with UTF-8 encoding
            stop_flag = self._stop_flags[job_id]
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=Path(__file__).parent.parent.parent,  # FactDB repo root
                env=env,
            )

            # Capture output line by line
            output_lines = []
            try:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    output_lines.append(line)
                    with self._lock:
                        job.output = "".join(output_lines)

                    # Check for stop request
                    if stop_flag.is_set():
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        break

                process.wait()
            except Exception as e:
                logger.exception(f"Error reading process output for job {job_id}: {e}")

            # Parse results from output
            self._parse_results(job, output_lines)

            # Mark as completed
            with self._lock:
                if stop_flag.is_set():
                    job.status = SeedingJobStatus.CANCELLED
                else:
                    job.status = SeedingJobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.exception(f"Error running seeding job {job_id}: {e}")
            with self._lock:
                job.status = SeedingJobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)

    def _parse_results(self, job: SeedingJob, output_lines: list[str]):
        """Parse seeding results from command output."""
        # This is a simplified parser; you can extend it to parse more detail
        job.results = []
        output_text = "".join(output_lines)

        # Look for project creation lines in output
        for line in output_lines:
            if "created:" in line.lower() or "project" in line.lower():
                # Try to extract project info
                # For now, we'll just count iterations
                job.current_iteration += 1


# Global job manager instance
_job_manager: Optional[SeededingJobManager] = None


def get_job_manager() -> SeededingJobManager:
    """Get the global job manager instance."""
    global _job_manager
    if _job_manager is None:
        _job_manager = SeededingJobManager()
    return _job_manager
