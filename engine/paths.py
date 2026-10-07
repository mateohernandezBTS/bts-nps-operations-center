from __future__ import annotations

import os
from pathlib import Path
import sys


DATA_ROOT_ENV_VAR = "BTS_SELAM_DATA_ROOT"


def bundled_resource_root() -> Path:
    """
    Return the root for bundled, read-only application resources.

    In source mode this is the repository root. In PyInstaller frozen
    mode this is the temporary extraction directory.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS).resolve()

    return Path(__file__).resolve().parent.parent


def application_root() -> Path:
    """
    Return the external application root.

    In source mode this is the repository root. In PyInstaller frozen
    mode this is the directory containing the executable.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


def data_root() -> Path:
    """
    Return the root for persistent operational data.

    BTS_SELAM_DATA_ROOT may override the default for future deployments.
    By default data lives under application_root.
    """
    configured_root = os.environ.get(DATA_ROOT_ENV_VAR, "").strip()

    if configured_root:
        return Path(configured_root).expanduser().resolve()

    return application_root()


def config_path(*parts: str) -> Path:
    """Resolve an externally editable configuration path."""
    return application_root() / "config" / Path(*parts)


def resource_path(*parts: str) -> Path:
    """Resolve a bundled static resource path."""
    return bundled_resource_root() / Path(*parts)


def data_path(*parts: str) -> Path:
    """Resolve a persistent operational data path."""
    return data_root() / Path(*parts)


def test_data_root() -> Path:
    """
    Return the root for isolated TEST operational data.

    Source mode preserves the certified repository tests directory.
    Frozen mode stores TEST data beside production data, under test_data.
    """
    if os.environ.get(DATA_ROOT_ENV_VAR, "").strip():
        return data_root() / "test_data"

    if getattr(sys, "frozen", False):
        return data_root() / "test_data"

    return repository_path("tests")


def test_data_path(*parts: str) -> Path:
    """Resolve a persistent TEST operational data path."""
    return test_data_root() / Path(*parts)


def session_directory(environment: str) -> Path:
    """Resolve the persistent session directory for one environment."""
    if environment.strip().upper() == "TEST":
        return test_data_path("runtime", "sessions")

    return data_path("runtime", "sessions")


def session_file_path(environment: str) -> Path:
    """Resolve current_session.json for one environment."""
    return session_directory(environment) / "current_session.json"


def repository_path(*parts: str) -> Path:
    """
    Resolve a source-tree path.

    This is intended for TEST paths, which are not part of production
    packaging and must remain isolated when running from the repository.
    """
    return Path(__file__).resolve().parent.parent / Path(*parts)


def resolve_configured_data_path(configured_path: str) -> Path:
    """Resolve a relative operational path under data_root."""
    path = Path(configured_path)

    if path.is_absolute():
        return path

    return data_root() / path


def resolve_configured_operational_path(
    configured_path: str,
    *,
    environment: str = "PRODUCTION",
) -> Path:
    """
    Resolve configured operational paths for PROD or TEST.

    TEST configs historically use paths prefixed with tests/. In frozen
    mode those paths map to data_root/test_data without using bundled tests.
    """
    path = Path(configured_path)

    if path.is_absolute():
        return path

    if environment.strip().upper() == "TEST":
        parts = path.parts

        if parts and parts[0].casefold() == "tests":
            return test_data_path(*parts[1:])

        return test_data_path(*parts)

    return data_root() / path
