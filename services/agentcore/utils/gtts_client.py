"""
gTTS Client for Text-to-Speech
Uses gTTS service running on port 8001
"""

import aiohttp
import logging
import os

logger = logging.getLogger(__name__)


class GTTSClient:
    """Client for gTTS service"""

    def __init__(self, endpoint: str = None):
        self.endpoint = endpoint or os.getenv("GTTS_ENDPOINT", "http://localhost:8001")
        self.session = None
        logger.info(f"GTTSClient initialized with endpoint: {self.endpoint}")

    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to speech audio (MP3 format)

        Args:
            text: Text to convert to speech

        Returns:
            Audio bytes in MP3 format
        """
        try:
            logger.info(f"Generating TTS for {len(text)} characters")

            session = await self._get_session()

            # Call gTTS service (OpenAI-compatible API)
            async with session.post(
                f"{self.endpoint}/v1/audio/speech",
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": "alloy",  # Default voice
                    "response_format": "mp3"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"gTTS API error: {response.status} - {error_text}")

                audio_bytes = await response.read()
                logger.info(f"TTS completed: {len(audio_bytes)} bytes")
                return audio_bytes

        except Exception as e:
            logger.error(f"Error in TTS: {e}", exc_info=True)
            raise
