from __future__ import annotations

from pathlib import Path


PRODUCT_NAME = "BTS SELAM NPS Operations Center"
RELEASE_ROOT_RELATIVE = Path("dist") / PRODUCT_NAME

APPROVED_CONFIG_FILES = (
    "business_rules.json",
    "operational_output.json",
    "report_detection.json",
    "report_sources.json",
    "system_config.json",
    "system_config_test.json",
    "weekly_schedule.json",
)

REQUIRED_PROD_DIRECTORIES = (
    Path("input") / "upcoming",
    Path("input") / "pending",
    Path("input") / "processing",
    Path("input") / "processed",
    Path("input") / "error",
    Path("output") / "runs",
    Path("output") / "weekly_runs",
    Path("logs"),
    Path("runtime") / "sessions",
)

REQUIRED_TEST_DIRECTORIES = (
    Path("test_data") / "input" / "power_automate" / "upcoming",
    Path("test_data") / "output",
    Path("test_data") / "logs",
    Path("test_data") / "runtime",
)

FORBIDDEN_EXTERNAL_DIRECTORIES = (
    "tests",
    "build",
    "__pycache__",
    "app",
    "engine",
)

FORBIDDEN_EXTERNAL_FILE_SUFFIXES = (
    ".py",
    ".pyc",
    ".eml",
)


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def validate_release(
    root: Path | None = None,
) -> list[str]:
    repository = root if root is not None else repository_root()
    release_root = repository / RELEASE_ROOT_RELATIVE
    errors: list[str] = []

    executable = release_root / f"{PRODUCT_NAME}.exe"
    if not executable.exists():
        errors.append(f"Missing executable: {executable}")

    internal = release_root / "_internal"
    if not internal.is_dir():
        errors.append(f"Missing _internal directory: {internal}")

    for config_name in APPROVED_CONFIG_FILES:
        config_path = release_root / "config" / config_name
        if not config_path.is_file():
            errors.append(f"Missing config file: {config_path}")

    for relative_directory in (
        REQUIRED_PROD_DIRECTORIES
        + REQUIRED_TEST_DIRECTORIES
    ):
        directory = release_root / relative_directory
        if not directory.is_dir():
            errors.append(f"Missing directory: {directory}")

    errors.extend(_find_forbidden_external_items(release_root))
    errors.extend(_find_unexpected_operational_files(release_root))

    return errors


def _find_forbidden_external_items(
    release_root: Path,
) -> list[str]:
    if not release_root.exists():
        return []

    errors: list[str] = []

    for path in release_root.rglob("*"):
        relative = path.relative_to(release_root)
        parts = relative.parts

        if parts and parts[0] == "_internal":
            continue

        if path.is_dir() and path.name in FORBIDDEN_EXTERNAL_DIRECTORIES:
            errors.append(f"Forbidden directory in release: {relative}")
            continue

        if path.is_file():
            if path.name.startswith("test_") and path.suffix == ".py":
                errors.append(f"Forbidden test file in release: {relative}")
                continue

            if path.suffix in FORBIDDEN_EXTERNAL_FILE_SUFFIXES:
                errors.append(f"Forbidden file in release: {relative}")
                continue

    return errors


def _find_unexpected_operational_files(
    release_root: Path,
) -> list[str]:
    errors: list[str] = []

    operational_roots = (
        release_root / "input",
        release_root / "output",
        release_root / "logs",
        release_root / "runtime",
        release_root / "test_data",
    )

    for operational_root in operational_roots:
        if not operational_root.exists():
            continue

        for path in operational_root.rglob("*"):
            if path.is_file():
                relative = path.relative_to(release_root)
                errors.append(
                    "Unexpected operational data file in release: "
                    f"{relative}"
                )

    return errors


def main() -> int:
    errors = validate_release()

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("RELEASE VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
