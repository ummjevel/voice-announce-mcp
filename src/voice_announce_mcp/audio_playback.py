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

    _try_players(
        path,
        (("paplay", []), ("aplay", []), ("ffplay", ["-nodisp", "-autoexit"])),
    )


def _try_players(
    path: str,
    players: tuple[tuple[str, list[str]], ...],
    required: bool = True,
) -> bool:
    """Try each installed player in order, falling through on failure.

    A player binary being present doesn't mean it can actually play audio
    (e.g. `aplay` exists but errors with no soundcard found when only the
    PulseAudio backend, not ALSA, is available) -- so a failure must fall
    through to the next candidate instead of raising immediately.
    """
    errors = []
    for player, extra_args in players:
        if not shutil.which(player):
            continue
        try:
            subprocess.run([player, *extra_args, path], check=True)
            return True
        except subprocess.CalledProcessError as e:
            errors.append(f"{player}: {e}")

    if required:
        tried = ", ".join(p for p, _ in players)
        detail = "; ".join(errors) if errors else "none installed"
        raise RuntimeError(f"No audio player found (tried {tried}) -- {detail}")
    return False


def _is_wsl() -> bool:
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False


def _play_on_wsl(path: str) -> None:
    # WSLg (Windows 11, WSL >= 0.67) exposes a working PulseAudio socket, so
    # paplay/aplay work directly, same as native Linux. Only aplay ships by
    # default on many WSLg images -- it's ALSA-only and fails with no
    # soundcard found unless pulseaudio-utils (paplay) is also installed, so
    # both must be tried rather than stopping at the first one found.
    if _try_players(path, (("paplay", []), ("aplay", [])), required=False):
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
