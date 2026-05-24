from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Iterable

from .errors import AdbCommandError


@dataclass(frozen=True)
class CommandOutput:
    args: list[str]
    stdout: str
    stderr: str
    returncode: int


class Adb:
    """Small wrapper around the adb executable."""

    def __init__(self, serial: str | None = None, adb_path: str = "adb", timeout: int = 20):
        self.serial = serial
        self.adb_path = adb_path
        self.timeout = timeout

    def command(self, args: Iterable[str]) -> list[str]:
        command = [self.adb_path]
        if self.serial:
            command += ["-s", self.serial]
        command += [str(arg) for arg in args]
        return command

    def run(
        self,
        *args: str,
        check: bool = True,
        timeout: int | None = None,
        strip: bool = True,
    ) -> str:
        command = self.command(args)
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout or self.timeout,
        )
        stdout = proc.stdout.strip() if strip else proc.stdout
        stderr = proc.stderr.strip() if strip else proc.stderr
        if check and proc.returncode != 0:
            raise AdbCommandError(command, proc.returncode, stdout, stderr)
        return stdout

    def output(
        self,
        *args: str,
        check: bool = True,
        timeout: int | None = None,
    ) -> CommandOutput:
        command = self.command(args)
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout or self.timeout,
        )
        if check and proc.returncode != 0:
            raise AdbCommandError(command, proc.returncode, proc.stdout, proc.stderr)
        return CommandOutput(command, proc.stdout, proc.stderr, proc.returncode)

    @classmethod
    def list_devices(cls, adb_path: str = "adb") -> list[str]:
        adb = cls(adb_path=adb_path)
        output = adb.run("devices")
        devices: list[str] = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices
