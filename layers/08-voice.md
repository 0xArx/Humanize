# Layer 8: Voice

**Gives the agent:** one voice on calls and on voice notes.
**Human needed:** none. **Cost:** free.
**Identity keys:** `voice.agentphone`, `voice.tts`

## Calls

AgentPhone ships a voice library. Pick one and set it on the agent (Layer 2 has the key and agent id):

```bash
curl -s -H "Authorization: Bearer <agentphone key>" https://api.agentphone.ai/v1/agents/voices
curl -s -X PATCH -H "Authorization: Bearer <agentphone key>" -H "Content-Type: application/json" \
  https://api.agentphone.ai/v1/agents/<agentId> -d '{"voice":"<voice_id>"}'
python3 humanize.py set voice.agentphone "<voice_id>"
```

## Voice notes and audio files

Local first, no account, no key:

```bash
# macOS
say -v Samantha -o hi.aiff "Hi, this is Ari." && ffmpeg -i hi.aiff hi.mp3
# any OS with Python: Microsoft's neural voices through the free edge-tts package (unofficial endpoint, may change)
pip install edge-tts
edge-tts --voice en-US-AriaNeural --text "Hi, this is Ari." --write-media hi.mp3
python3 humanize.py set voice.tts "edge-tts en-US-AriaNeural"
```

Pick the neural voice closest to the AgentPhone one so calls and notes sound like the same person. For an offline voice use Piper. To hear voice notes sent to the agent, transcribe locally with `faster-whisper` (`pip install faster-whisper`).

> Status (2026-09-21): AgentPhone voice endpoints read from the vendor's docs. edge-tts and faster-whisper exist on PyPI. Not exercised.
