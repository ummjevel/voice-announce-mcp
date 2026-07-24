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

Early scaffold, built while a smaller on-device FreyaTTS pretrain
(88M/127M/183M) is running in a separate project -- **not yet installed or
tested end-to-end on macOS or native Windows.** The WSL2/Linux code paths
were written and reasoned through on a headless Linux dev box, not verified
against real audio hardware either. Treat this as a first pass to react to,
not a finished tool.

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
| `VOICE_MCP_MODEL` | `ummjevel/freyatts-ko-voiceA` | **Not published to HF yet.** Until it is, point this at a local checkpoint dir, e.g. `/data/users/voice/zoey/FreyaTTS/checkpoints/distill_voiceA/final`. Can also be any other HF repo id in the same format. |
| `VOICE_MCP_DEVICE` | auto (`cuda` > `mps` > `cpu`) | Override if auto-detection picks wrong |
| `VOICE_MCP_STEPS` | `32` | ODE sampling steps; lower = faster, some quality loss. Untested below 32 so far -- see FreyaTTS's `sample()` |
| `VOICE_MCP_SEED` | `9` | Voice identity (FreyaTTS has no speaker embedding -- seed *is* the voice). `9` = voiceA's locked seed per `confirmed_voices/best_seeds.json` |

## Install

```sh
cd voice-announce-mcp
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

The `freyatts` dependency installs from `github.com/ummjevel/FreyaTTS` via
git -- that repo needs to be public (or installed separately as an editable
local checkout) for this to resolve.

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

- No installed/verified run yet -- next step is a smoke test end-to-end on
  at least one real machine per platform.
- `VOICE_MCP_MODEL` default points at an unpublished HF repo; needs the
  actual FreyaTTS Korean checkpoint pushed (see `FreyaTTS` repo, blocked on
  git push auth as of 2026-07-24) before the default is usable out of the box.
- No quality/latency tuning done here yet -- `FreyaTTS/README.md`'s
  Evaluation section has the levers (ODE step count, model size) if
  `announce()` turns out too slow in practice.
