import os
import tempfile

from mcp.server.fastmcp import FastMCP

from .audio_playback import play_audio
from .tts_engine import get_engine

mcp = FastMCP("voice-announce")


@mcp.tool()
def announce(text: str) -> str:
    """Speak a short summary out loud through the local speakers.

    Call this with a very short summary (1-2 lines), written entirely in
    Korean, of what you just did or found -- write the summary yourself
    first, then pass only that summary text here. Do not pass long text or
    non-Korean text; this is for a spoken announcement, not a document.
    """
    engine = get_engine()
    fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        engine.synthesize_to_file(text, out_path)
        play_audio(out_path)
    finally:
        os.remove(out_path)
    return f"Announced ({len(text)} chars)."


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
