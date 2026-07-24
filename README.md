# voice-announce-mcp

An MCP server that turns a short text summary into spoken audio and plays it
locally. Built for Claude Code / Codex to **speak a summary of what just
happened** at the end of a task -- the coding agent writes the summary
itself (that's what it's already good at); this server only does
text -> speech -> playback.

Uses [FreyaTTS](https://github.com/ummjevel/FreyaTTS) (Korean fork,
distilled from Qwen3-TTS) for synthesis. Runs on CUDA, Apple Silicon (MPS),
or CPU, auto-detected.

## Status

Core pipeline (load model -> synthesize -> write wav) verified working
end-to-end on Linux/CPU with a local checkpoint, in a clean venv with only
the declared `pyproject.toml` dependencies (no manual PYTHONPATH). **Not yet
tested on macOS or native Windows**, and the audio-playback code for those
platforms is best-effort, not hardware-verified. GPU inference also untested
on this dev box (its driver is older than the CUDA version the default pip
`torch` wheel needs -- not an issue on a normal desktop/laptop with current
drivers).

## How it works

- One MCP tool, `announce(text: str)`. The calling model (Claude Code /
  Codex) is expected to write its own short (1-3 sentence) summary and pass
  it in -- this server does no summarization itself.
- The FreyaTTS model loads once at server startup (~10s) and stays resident,
  so repeated `announce()` calls are fast. This is why it's an MCP server
  and not a per-call script/Skill.
- Model source is configurable: a local checkpoint directory, or any Hugging
  Face repo id that follows FreyaTTS's `config.json` + `model.safetensors`
  layout (`FreyaTTS.from_pretrained` resolves both).

## Configuration (environment variables)

| Variable | Default | Notes |
| --- | --- | --- |
| `VOICE_MCP_MODEL` | `ummjevel/freyatts-ko-voiceA` | **Not published to HF yet.** Until it is, point this at a local checkpoint dir *converted* to `from_pretrained` format (`config.json` + `model.safetensors`), e.g. `FreyaTTS/checkpoints/distill_voiceA/final/hf` -- run `python training/convert_ckpt.py checkpoints/distill_voiceA/final/model.pt --out checkpoints/distill_voiceA/final/hf` first if that `hf/` subfolder doesn't exist yet. Once published to HF in this same converted format, no local conversion step is needed at all. |
| `VOICE_MCP_DEVICE` | auto (`cuda` > `mps` > `cpu`) | Override if auto-detection picks wrong |
| `VOICE_MCP_STEPS` | `32` | ODE sampling steps; lower = faster, some quality loss. Untested below 32 so far -- see FreyaTTS's `sample()` |
| `VOICE_MCP_SEED` | `9` | Voice identity (FreyaTTS has no speaker embedding -- seed *is* the voice). `9` = voiceA's locked seed per `confirmed_voices/best_seeds.json` |

## Install

### Non-developers (recommended): one command, no manual venv

Use [`uv`](https://docs.astral.sh/uv/) rather than `pipx`. Both install a
Python CLI into its own isolated environment, but `uv` can also **fetch and
use a specific Python version itself** -- the user's `python3` doesn't need
to already be a supported version. This matters here: a brand-new Python
(e.g. 3.14) routinely breaks `pip`/build tooling for packages like this one
that pull in compiled dependencies (torch, etc.), with confusing internal
errors instead of a clean version-mismatch message -- pinning the
interpreter `uv` uses sidesteps that entirely, regardless of what's already
on the user's machine.

```sh
# one-time, if uv isn't already installed:
#   macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh
#   Windows:     powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

uv tool install --python 3.12 "voice-announce-mcp @ git+https://github.com/ummjevel/voice-announce-mcp.git"
```

`--python 3.12` tells `uv` to download and use that interpreter for this
tool specifically (it does not touch or require any system Python). This
pulls in `freyatts` (and its own dependencies: torch, voxcpm, etc.)
automatically -- `freyatts` is now a proper pip package (see
`FreyaTTS/pyproject.toml`) -- so it's a single command with nothing to clone
or convert by hand, as long as `VOICE_MCP_MODEL` points at a ready-to-use
checkpoint (a published HF repo id, once one exists -- see Known gaps).

**Note:** the exact `uv tool install` flags above are our best understanding
of `uv`'s CLI, not yet run against a real `uv` install end to end -- if the
syntax has drifted, `uv tool install --help` has the current form. `pipx`
works too (`pipx install git+https://...`), just without the
Python-version-pinning safety net -- only use it if the system's default
`python3` is already in the `>=3.10,<3.14` range this project supports.

### Developers (editable install)

```sh
cd voice-announce-mcp
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Verified (2026-07-24) in a clean venv against a local FreyaTTS checkout:
`pip install -e .` resolves `freyatts` and all other dependencies with no
manual `PYTHONPATH` needed, **once both this repo and FreyaTTS's
`pyproject.toml` commit are pushed** -- pip fetches `freyatts` straight from
`github.com/ummjevel/FreyaTTS` via git.

## Register with Claude Code

```sh
claude mcp add voice-announce -- voice-announce-mcp
```

or, with an explicit local model while unpublished:

```sh
claude mcp add voice-announce -e VOICE_MCP_MODEL=/path/to/checkpoints/distill_voiceA/final -- voice-announce-mcp
```

## Register with Codex

Codex's MCP config syntax may differ by version -- check
`codex mcp --help` / the current Codex docs before trusting this verbatim.
As of this writing it's roughly a `~/.codex/config.toml` entry:

```toml
[mcp_servers.voice-announce]
command = "voice-announce-mcp"
env = { VOICE_MCP_MODEL = "/path/to/checkpoints/distill_voiceA/final" }
```

## Audio playback per platform

| Platform | Method |
| --- | --- |
| macOS | `afplay` |
| Windows | PowerShell `Media.SoundPlayer` |
| WSL2 (WSLg / Win11) | `paplay`/`aplay` via the PulseAudio socket WSLg exposes |
| WSL2 (no WSLg) | Crosses the interop boundary, plays via `powershell.exe` on the Windows side |
| Linux | `paplay` / `aplay` / `ffplay`, whichever is found first |

## Known gaps / next steps

- Core pipeline verified on Linux/CPU only so far -- next step is a smoke
  test on real macOS and Windows hardware (playback code especially).
- `VOICE_MCP_MODEL` default points at an unpublished HF repo. Publish it
  **already converted** to `config.json` + `model.safetensors` format
  (i.e. push the `hf/` output of `convert_ckpt.py`, not the raw training
  `model.pt`) so end users never need to run the converter themselves.
- No quality/latency tuning done here yet -- `FreyaTTS/README.md`'s
  Evaluation section has the levers (ODE step count, model size) if
  `announce()` turns out too slow in practice.
- Not yet on PyPI, so `pipx install` currently means `pipx install git+...`
  (slower first install, rebuilds from source) rather than a prebuilt wheel.
