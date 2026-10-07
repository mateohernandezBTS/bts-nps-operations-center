from __future__ import annotations

import shutil
import subprocess
import sys
import stat
from pathlib import Path

from validate_release import (
    APPROVED_CONFIG_FILES,
    PRODUCT_NAME,
    REQUIRED_PROD_DIRECTORIES,
    REQUIRED_TEST_DIRECTORIES,
    RELEASE_ROOT_RELATIVE,
    validate_release,
)


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def clean_packaging_artifacts(root: Path) -> None:
    for name in ("build", "dist"):
        target = root / name
        if target.exists():
            _remove_packaging_directory(root, target)

    spec_path = root / f"{PRODUCT_NAME}.spec"
    if spec_path.exists():
        spec_path.unlink()


def run_pyinstaller(root: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onedir",
        "--windowed",
        "--name",
        PRODUCT_NAME,
        "--version-file",
        str(root / "packaging" / "windows_version_info.txt"),
        "--paths",
        ".",
        str(root / "app" / "nps_operations_center.py"),
    ]

    result = subprocess.run(
        command,
        cwd=root,
        check=False,
    )

    if result.returncode != 0:
        raise SystemExit(result.returncode)


def prepare_external_layout(root: Path) -> Path:
    release_root = root / RELEASE_ROOT_RELATIVE
    config_root = release_root / "config"
    config_root.mkdir(parents=True, exist_ok=True)

    for config_name in APPROVED_CONFIG_FILES:
        source = root / "config" / config_name
        destination = config_root / config_name

        if not source.exists():
            raise FileNotFoundError(
                f"Missing approved config file: {source}"
            )

        shutil.copy2(source, destination)

    for relative_directory in (
        REQUIRED_PROD_DIRECTORIES
        + REQUIRED_TEST_DIRECTORIES
    ):
        (release_root / relative_directory).mkdir(
            parents=True,
            exist_ok=True,
        )

    return release_root


def remove_temporary_spec(root: Path) -> None:
    spec_path = root / f"{PRODUCT_NAME}.spec"
    if spec_path.exists():
        spec_path.unlink()


def build_release() -> Path:
    root = repository_root()

    clean_packaging_artifacts(root)
    run_pyinstaller(root)
    release_root = prepare_external_layout(root)
    remove_temporary_spec(root)

    errors = validate_release(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    print("BUILD SUCCESS")
    print(f"Executable: {release_root / (PRODUCT_NAME + '.exe')}")
    print(f"Release root: {release_root}")
    print("Config files:")
    for config_name in APPROVED_CONFIG_FILES:
        print(f"  - {config_name}")
    print("Layout validation: RELEASE VALIDATION PASSED")

    return release_root


def _remove_packaging_directory(
    root: Path,
    target: Path,
) -> None:
    resolved_root = root.resolve()
    resolved_target = target.resolve()

    if resolved_target.parent != resolved_root:
        raise RuntimeError(
            f"Refusing to remove non-packaging directory: {target}"
        )

    if resolved_target.name not in {"build", "dist"}:
        raise RuntimeError(
            f"Refusing to remove unexpected directory: {target}"
        )

    shutil.rmtree(
        resolved_target,
        onexc=_clear_readonly_and_retry,
    )


def _clear_readonly_and_retry(
    function,
    path,
    excinfo,
) -> None:
    target = Path(path)
    target.chmod(
        target.stat().st_mode
        | stat.S_IWRITE
    )
    function(path)


if __name__ == "__main__":
    build_release()
