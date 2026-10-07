from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
import shutil
import uuid

from engine.paths import config_path, resolve_configured_operational_path


SYSTEM_CONFIG_FILE = (
    config_path("system_config.json")
)


@dataclass
class ExecutionContext:
    execution_id: str
    environment: str
    source_file: str
    original_path: str
    processing_path: str
    run_directory: str
    started_at: str
    finished_at: str = ""
    execution_status: str = "STARTED"
    current_stage: str = "INITIALIZATION"
    issues: list[str] = field(default_factory=list)


def clean_text(value) -> str:
    """Limpia valores de texto."""
    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def load_json(path: Path) -> dict:
    """Carga un archivo JSON."""
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_json(
    data: dict,
    output_path: Path,
) -> None:
    """Guarda un diccionario como JSON."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def resolve_project_path(
    configured_path: str,
    *,
    environment: str = "PRODUCTION",
) -> Path:
    """Convierte una ruta relativa en una ruta operativa."""
    return resolve_configured_operational_path(
        configured_path,
        environment=environment,
    )


def generate_execution_id() -> str:
    """
    Genera un identificador único.

    Ejemplo:
    20260729_124500_a1b2c3
    """
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    unique_suffix = uuid.uuid4().hex[:6]

    return f"{timestamp}_{unique_suffix}"


def ensure_directories(config: dict) -> dict[str, Path]:
    """Crea y devuelve las carpetas del ciclo de vida."""
    lifecycle = config.get(
        "input_lifecycle",
        {},
    )

    output_config = config.get(
        "output",
        {},
    )

    logs_config = config.get(
        "logs",
        {},
    )
    environment = clean_text(
        config.get(
            "environment",
            "PRODUCTION",
        )
    )

    directories = {
        "pending": resolve_project_path(
            lifecycle.get(
                "pending_directory",
                "input/pending",
            ),
            environment=environment,
        ),
        "processing": resolve_project_path(
            lifecycle.get(
                "processing_directory",
                "input/processing",
            ),
            environment=environment,
        ),
        "processed": resolve_project_path(
            lifecycle.get(
                "processed_directory",
                "input/processed",
            ),
            environment=environment,
        ),
        "error": resolve_project_path(
            lifecycle.get(
                "error_directory",
                "input/error",
            ),
            environment=environment,
        ),
        "runs": resolve_project_path(
            output_config.get(
                "runs_directory",
                "output/runs",
            ),
            environment=environment,
        ),
        "logs": resolve_project_path(
            logs_config.get(
                "directory",
                "logs",
            ),
            environment=environment,
        ),
    }

    for directory in directories.values():
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    return directories


def move_without_overwrite(
    source_path: Path,
    destination_directory: Path,
    execution_id: str,
) -> Path:
    """
    Mueve un archivo evitando sobrescribir otro con el mismo nombre.
    """
    destination_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination_path = (
        destination_directory
        / source_path.name
    )

    if destination_path.exists():
        destination_path = (
            destination_directory
            / f"{source_path.stem}_{execution_id}{source_path.suffix}"
        )

    return Path(
        shutil.move(
            str(source_path),
            str(destination_path),
        )
    )


def create_execution(
    source_path: Path,
    config: dict,
    directories: dict[str, Path],
) -> ExecutionContext:
    """Crea el contexto y mueve el archivo a processing."""
    if not source_path.exists():
        raise FileNotFoundError(
            f"No existe el archivo pendiente:\n{source_path}"
        )

    execution_id = generate_execution_id()

    run_directory = (
        directories["runs"]
        / execution_id
    )

    run_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    processing_path = move_without_overwrite(
        source_path=source_path,
        destination_directory=directories["processing"],
        execution_id=execution_id,
    )

    context = ExecutionContext(
        execution_id=execution_id,
        environment=clean_text(
            config.get(
                "environment",
                "TEST",
            )
        ),
        source_file=source_path.name,
        original_path=str(source_path),
        processing_path=str(processing_path),
        run_directory=str(run_directory),
        started_at=datetime.now().isoformat(),
    )

    write_execution_manifest(context)

    return context


def write_execution_manifest(
    context: ExecutionContext,
) -> None:
    """Actualiza el manifiesto dentro de la carpeta de ejecución."""
    run_directory = Path(
        context.run_directory
    )

    manifest_path = (
        run_directory
        / "execution_manifest.json"
    )

    save_json(
        asdict(context),
        manifest_path,
    )


def write_execution_log(
    context: ExecutionContext,
    directories: dict[str, Path],
) -> Path:
    """Guarda una copia final del manifiesto en logs."""
    log_path = (
        directories["logs"]
        / f"{context.execution_id}.json"
    )

    save_json(
        asdict(context),
        log_path,
    )

    return log_path


def update_execution(
    context: ExecutionContext,
    stage: str,
    status: str | None = None,
    issue: str | None = None,
) -> None:
    """Actualiza la etapa y estado de una ejecución."""
    context.current_stage = stage

    if status:
        context.execution_status = status

    if issue:
        context.issues.append(issue)

    write_execution_manifest(context)


def return_to_pending_after_test(
    context: ExecutionContext,
    directories: dict[str, Path],
) -> Path:
    """
    Devuelve el archivo a pending.

    Solo se utiliza durante la prueba del administrador de ejecución.
    """
    processing_path = Path(
        context.processing_path
    )

    returned_path = move_without_overwrite(
        source_path=processing_path,
        destination_directory=directories["pending"],
        execution_id=context.execution_id,
    )

    context.processing_path = ""
    context.finished_at = datetime.now().isoformat()
    context.execution_status = "TEST_COMPLETED"
    context.current_stage = "LIFECYCLE_TEST_COMPLETED"

    write_execution_manifest(context)
    write_execution_log(
        context=context,
        directories=directories,
    )

    return returned_path

def complete_execution(
    context: ExecutionContext,
    directories: dict[str, Path],
) -> Path:
    """Finaliza una ejecución exitosa y mueve el correo a processed."""
    processing_path = Path(
        context.processing_path
    )

    if not processing_path.exists():
        raise FileNotFoundError(
            "No se encontró el archivo en processing:\n"
            f"{processing_path}"
        )

    processed_path = move_without_overwrite(
        source_path=processing_path,
        destination_directory=directories["processed"],
        execution_id=context.execution_id,
    )

    context.processing_path = str(
        processed_path
    )
    context.finished_at = datetime.now().isoformat()
    context.execution_status = "COMPLETED"
    context.current_stage = "COMPLETED"

    write_execution_manifest(context)

    write_execution_log(
        context=context,
        directories=directories,
    )

    return processed_path

def fail_execution(
    context: ExecutionContext,
    directories: dict[str, Path],
    error_message: str,
) -> Path | None:
    """Registra una falla y mueve el correo a error."""
    context.finished_at = datetime.now().isoformat()
    context.execution_status = "FAILED"
    context.current_stage = "ERROR"
    context.issues.append(error_message)

    processing_path = Path(
        context.processing_path
    )

    error_path = None

    if processing_path.exists():
        error_path = move_without_overwrite(
            source_path=processing_path,
            destination_directory=directories["error"],
            execution_id=context.execution_id,
        )

        context.processing_path = str(
            error_path
        )

    write_execution_manifest(context)
    write_execution_log(
        context=context,
        directories=directories,
    )

    return error_path


def load_system_config() -> dict:
    """Carga la configuración general."""
    if not SYSTEM_CONFIG_FILE.exists():
        raise FileNotFoundError(
            "No se encontró la configuración:\n"
            f"{SYSTEM_CONFIG_FILE}"
        )

    return load_json(
        SYSTEM_CONFIG_FILE
    )
