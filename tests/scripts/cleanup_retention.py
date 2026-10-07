from datetime import datetime, timedelta
import json
from pathlib import Path
import shutil


SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = SCRIPT_DIR.parent
PROJECT_DIR = TESTS_DIR.parent

CONFIG_FILE = PROJECT_DIR / "config" / "system_config.json"


def load_json(path: Path) -> dict:
    """Carga un archivo JSON."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def resolve_project_path(relative_path: str) -> Path:
    """Convierte una ruta configurada en una ruta absoluta del proyecto."""
    return PROJECT_DIR / relative_path


def get_modified_datetime(path: Path) -> datetime:
    """Obtiene la fecha de última modificación."""
    return datetime.fromtimestamp(path.stat().st_mtime)


def find_expired_items(
    directory: Path,
    retention_days: int,
    now: datetime,
) -> list[dict]:
    """Encuentra archivos y carpetas fuera del período de retención."""
    if not directory.exists():
        return []

    cutoff = now - timedelta(days=retention_days)
    expired_items = []

    for item in directory.iterdir():
        modified_at = get_modified_datetime(item)

        if modified_at < cutoff:
            expired_items.append(
                {
                    "path": item,
                    "modified_at": modified_at,
                    "cutoff": cutoff,
                }
            )

    return expired_items


def delete_item(path: Path) -> None:
    """Elimina un archivo o una carpeta completa."""
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def process_retention_area(
    area_name: str,
    directory: Path,
    retention_days: int,
    dry_run: bool,
    now: datetime,
) -> dict:
    """Evalúa y, si corresponde, elimina elementos expirados."""
    expired_items = find_expired_items(
        directory=directory,
        retention_days=retention_days,
        now=now,
    )

    deleted_count = 0

    print()
    print(f"{area_name}")
    print("-" * 80)
    print(f"Carpeta: {directory}")
    print(f"Retención: {retention_days} días")
    print(f"Elementos expirados: {len(expired_items)}")

    for item in expired_items:
        path = item["path"]
        modified_at = item["modified_at"]

        if dry_run:
            action = "SIMULACIÓN: se eliminaría"
        else:
            delete_item(path)
            deleted_count += 1
            action = "ELIMINADO"

        print(
            f"{action} | "
            f"{modified_at:%Y-%m-%d %H:%M:%S} | "
            f"{path.name}"
        )

    return {
        "area": area_name,
        "directory": str(directory),
        "retention_days": retention_days,
        "expired_count": len(expired_items),
        "deleted_count": deleted_count,
    }


def main() -> None:
    print("=" * 80)
    print("LIMPIEZA POR POLÍTICA DE RETENCIÓN NPS")
    print("=" * 80)

    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró la configuración:\n{CONFIG_FILE}"
        )

    config = load_json(CONFIG_FILE)
    retention = config.get("retention", {})

    if not retention.get("enabled", True):
        print("La política de retención está desactivada.")
        return

    dry_run = retention.get("dry_run", True)
    now = datetime.now()

    lifecycle = config.get("input_lifecycle", {})
    output_config = config.get("output", {})
    log_config = config.get("logs", {})

    areas = [
        {
            "name": "INPUT PROCESSED",
            "directory": resolve_project_path(
                lifecycle.get(
                    "processed_directory",
                    "input/processed",
                )
            ),
            "days": int(
                retention.get("processed_days", 30)
            ),
        },
        {
            "name": "INPUT ERROR",
            "directory": resolve_project_path(
                lifecycle.get(
                    "error_directory",
                    "input/error",
                )
            ),
            "days": int(
                retention.get("error_days", 90)
            ),
        },
        {
            "name": "OUTPUT RUNS",
            "directory": resolve_project_path(
                output_config.get(
                    "runs_directory",
                    "output/runs",
                )
            ),
            "days": int(
                retention.get("output_runs_days", 90)
            ),
        },
        {
            "name": "LOGS",
            "directory": resolve_project_path(
                log_config.get(
                    "directory",
                    "logs",
                )
            ),
            "days": int(
                retention.get("log_days", 90)
            ),
        },
    ]

    print(f"Fecha de ejecución: {now:%Y-%m-%d %H:%M:%S}")
    print(f"Modo simulación: {dry_run}")

    results = []

    for area in areas:
        results.append(
            process_retention_area(
                area_name=area["name"],
                directory=area["directory"],
                retention_days=area["days"],
                dry_run=dry_run,
                now=now,
            )
        )

    total_expired = sum(
        result["expired_count"]
        for result in results
    )

    total_deleted = sum(
        result["deleted_count"]
        for result in results
    )

    print()
    print("=" * 80)
    print("RESUMEN")
    print("-" * 80)
    print(f"Elementos expirados detectados: {total_expired}")
    print(f"Elementos eliminados: {total_deleted}")

    if dry_run:
        print(
            "No se eliminó ningún archivo porque "
            "retention.dry_run = true."
        )
    else:
        print("La política de retención fue aplicada.")

    print("=" * 80)


if __name__ == "__main__":
    main()