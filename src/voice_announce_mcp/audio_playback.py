"""Cross-platform, synchronous audio playback: macOS, native Windows, and WSL2.

Only tested on Linux/WSL2-shaped environments so far (this was written on a
headless Linux dev box) -- the macOS and native-Windows branches are
best-effort from documented tool behavior, not yet verified on real hardware.
Flag it if `afplay`/PowerShell playback doesn't work as expected.
"""

import platform
import shutil
import subprocess


def play_audio(path: str) -> None:
    system = platform.system()

    if system == "Darwin":
        subprocess.run(["afplay", path], check=True)
        return

    if system == "Windows":
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(New-Object Media.SoundPlayer '{path}').PlaySync();",
            ],
            check=True,
        )
        return

    # Linux, including WSL2.
    if _is_wsl():
        _play_on_wsl(path)
        return

    for player, extra_args in (("paplay", []), ("aplay", []), ("ffplay", ["-nodisp", "-autoexit"])):
        if shutil.which(player):
            subprocess.run([player, *extra_args, path], check=True)
            return

    raise RuntimeError("No audio player found (tried paplay, aplay, ffplay)")


def _is_wsl() -> bool:
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False


def _play_on_wsl(path: str) -> None:
    # WSLg (Windows 11, WSL >= 0.67) exposes a working PulseAudio socket, so
    # paplay/aplay work directly, same as native Linux.
    for player in ("paplay", "aplay"):
        if shutil.which(player):
            subprocess.run([player, path], check=True)
            return

    # Older WSL2 without WSLg has no audio device at all -- cross the
    # interop boundary and let PowerShell.exe play it on the Windows side.
    if shutil.which("powershell.exe"):
        win_path = _to_windows_path(path)
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f"(New-Object Media.SoundPlayer '{win_path}').PlaySync();",
            ],
            check=True,
        )
        return

    raise RuntimeError(
        "WSL2 audio playback unavailable: no paplay/aplay (WSLg) and no "
        "powershell.exe interop found"
    )


def _to_windows_path(path: str) -> str:
    result = subprocess.run(["wslpath", "-w", path], capture_output=True, text=True, check=True)
    return result.stdout.strip()
