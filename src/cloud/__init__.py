"""Cloud MVP — fully self-hosted translation/ASR/TTS using free models.

This sub-package is the runnable proof-of-concept that powers the Streamlit
UI: NLLB-200 for translation, OpenAI-Whisper (offline) for speech recognition
and Meta MMS-TTS for Turkmen synthesis. It deliberately depends only on
open-source weights so the whole flow works without any external API keys.

For the abstract, provider-pluggable architecture used by the FastAPI
service, see ``src.translator`` / ``src.speech`` / ``src.video``.
"""
