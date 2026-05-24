class SummerAutomationError(RuntimeError):
    """Base exception for this package."""


class AdbCommandError(SummerAutomationError):
    """Raised when an ADB command fails."""

    def __init__(self, command: list[str], returncode: int, stdout: str, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(
            f"ADB command failed ({returncode}): {' '.join(command)}\n{stderr or stdout}"
        )


class UiElementNotFound(SummerAutomationError):
    """Raised when a required UI node cannot be found."""


class SafetyError(SummerAutomationError):
    """Raised when a safety rule blocks an action."""


class AppStateError(SummerAutomationError):
    """Raised when the app is not in the expected activity or page state."""


class DeviceSelectionError(SummerAutomationError):
    """Raised when an ADB device cannot be selected automatically."""
