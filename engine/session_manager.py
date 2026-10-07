from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any
import uuid

from engine.paths import data_path


DEFAULT_SESSION_DIRECTORY = (
    data_path("runtime", "sessions")
)

DEFAULT_SESSION_FILE = (
    DEFAULT_SESSION_DIRECTORY
    / "current_session.json"
)


class SessionManagerError(Exception):
    """Raised when the application session cannot be managed."""


@dataclass
class ApplicationSession:
    """
    Persistent operational state for the NPS application.
    """

    session_id: str
    environment: str
    status: str
    operation: str
    reference_date: str
    weekly_run_id: str
    current_stage: str
    current_source: str
    message: str
    started_at: str
    updated_at: str
    finished_at: str = ""
    issues: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)


def current_timestamp() -> str:
    """Return a portable ISO timestamp."""
    return datetime.now().isoformat(
        timespec="seconds"
    )


def generate_session_id() -> str:
    """Generate a unique application session identifier."""
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    suffix = uuid.uuid4().hex[:6]

    return f"{timestamp}_{suffix}"


class SessionManager:
    """
    Create, update, read, and finish the current
    application session.

    The session manager does not execute business logic.
    It only persists operational state.
    """

    def __init__(
        self,
        session_file: Path | str | None = None,
    ) -> None:
        self.session_file = Path(
            session_file
            if session_file is not None
            else DEFAULT_SESSION_FILE
        )

    def save(
        self,
        session: ApplicationSession,
    ) -> Path:
        """
        Persist the current session as JSON.
        """
        self.session_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            with self.session_file.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    asdict(session),
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
        except OSError as exc:
            raise SessionManagerError(
                "The application session could not be saved: "
                f"{exc}"
            ) from exc

        return self.session_file

    def load(self) -> ApplicationSession | None:
        """
        Return the latest persisted session.

        Return None when no session has been created yet.
        """
        if not self.session_file.exists():
            return None

        try:
            with self.session_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise SessionManagerError(
                "The application session file is invalid: "
                f"{exc}"
            ) from exc
        except OSError as exc:
            raise SessionManagerError(
                "The application session could not be read: "
                f"{exc}"
            ) from exc

        try:
            return ApplicationSession(
                **data
            )
        except TypeError as exc:
            raise SessionManagerError(
                "The application session structure is invalid: "
                f"{exc}"
            ) from exc

    def create(
        self,
        *,
        environment: str,
        operation: str,
        reference_date: str,
        weekly_run_id: str = "",
        status: str = "STARTED",
        current_stage: str = "INITIALIZATION",
        message: str = "",
    ) -> ApplicationSession:
        """
        Create and persist a new operational session.
        """
        timestamp = current_timestamp()

        session = ApplicationSession(
            session_id=generate_session_id(),
            environment=environment,
            status=status,
            operation=operation,
            reference_date=reference_date,
            weekly_run_id=weekly_run_id,
            current_stage=current_stage,
            current_source="",
            message=message,
            started_at=timestamp,
            updated_at=timestamp,
        )

        self.save(session)

        return session

    def update(
        self,
        session: ApplicationSession,
        *,
        status: str | None = None,
        current_stage: str | None = None,
        current_source: str | None = None,
        message: str | None = None,
        weekly_run_id: str | None = None,
        issues: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
        outputs: dict[str, str] | None = None,
    ) -> ApplicationSession:
        """
        Update selected fields and persist the session.
        """
        if status is not None:
            session.status = status

        if current_stage is not None:
            session.current_stage = current_stage

        if current_source is not None:
            session.current_source = current_source

        if message is not None:
            session.message = message

        if weekly_run_id is not None:
            session.weekly_run_id = weekly_run_id

        if issues is not None:
            session.issues = list(issues)

        if metrics is not None:
            session.metrics = dict(metrics)

        if outputs is not None:
            session.outputs = dict(outputs)

        session.updated_at = current_timestamp()

        self.save(session)

        return session

    def finish(
        self,
        session: ApplicationSession,
        *,
        status: str,
        message: str,
        issues: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
        outputs: dict[str, str] | None = None,
    ) -> ApplicationSession:
        """
        Mark a session as finished and persist its final state.
        """
        timestamp = current_timestamp()

        session.status = status
        session.current_stage = "FINISHED"
        session.message = message
        session.updated_at = timestamp
        session.finished_at = timestamp

        if issues is not None:
            session.issues = list(issues)

        if metrics is not None:
            session.metrics = dict(metrics)

        if outputs is not None:
            session.outputs = dict(outputs)

        self.save(session)

        return session

    def reset(self) -> None:
        """
        Delete the persisted current session.

        This does not delete processing outputs or logs.
        """
        if not self.session_file.exists():
            return

        try:
            self.session_file.unlink()
        except OSError as exc:
            raise SessionManagerError(
                "The application session could not be reset: "
                f"{exc}"
            ) from exc
