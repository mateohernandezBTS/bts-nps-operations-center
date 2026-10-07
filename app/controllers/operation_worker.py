from __future__ import annotations

import traceback
from typing import Callable

from PySide6.QtCore import QObject, Signal, Slot

from app.controllers.ui_controller import UIActionResult
from engine.operational_logging import persist_application_error


class OperationWorker(QObject):
    """
    Execute one UI controller operation outside the main UI thread.

    The worker contains no business logic. It only invokes the supplied
    callable and reports its result back to the application shell.
    """

    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        operation: Callable[[], UIActionResult],
        *,
        environment: str = "PRODUCTION",
        operation_name: str = "UI_OPERATION",
    ) -> None:
        super().__init__()

        self._operation = operation
        self._environment = environment
        self._operation_name = operation_name

    @Slot()
    def run(self) -> None:
        """
        Execute the configured operation and emit its result.
        """

        try:
            result = self._operation()
        except Exception as exc:
            persist_application_error(
                environment=self._environment,
                component="OperationWorker",
                operation=self._operation_name,
                error=exc,
                traceback_text=traceback.format_exc(),
            )
            self.failed.emit(str(exc))
        else:
            self.completed.emit(result)
        finally:
            self.finished.emit()
