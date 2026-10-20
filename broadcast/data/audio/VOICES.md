# Voices

Speech is not configured. No short name has been chosen.

Set `SPEECH_KEY` and `SPEECH_REGION`, then run `python tools/build_cache.py` from `broadcast/`. The build reads the neural voices on that resource and writes the six short names here.

The script cache is 96112 characters of SSML, under the 100,000 character stop. That count uses the placeholder voice name `pending-voice-name`.
