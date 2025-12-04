"""
vLLM Client for ASR and Q&A
Uses vLLM API with prompt engineering for transcription and Q&A
"""

import aiohttp
import logging
import os
from typing import List, Dict

logger = logging.getLogger(__name__)


class VLLMClient:
    """Client for vLLM API with ASR and Q&A capabilities"""

    def __init__(self, endpoint: str = None):
        self.endpoint = endpoint or os.getenv("VLLM_ENDPOINT", "http://localhost:8000")
        self.session = None
        logger.info(f"VLLMClient initialized with endpoint: {self.endpoint}")

    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def transcribe_audio(self, audio_path: str) -> str:
        """
        Transcribe audio using vLLM chat completions with ASR prompt

        Uses the validated Phase 0 approach: vLLM prompting for transcription
        """
        try:
            logger.info(f"Transcribing audio: {audio_path}")

            session = await self._get_session()

            # Construct chat completions request with audio
            # Using the Phase 0 validated approach
            async with session.post(
                f"{self.endpoint}/v1/chat/completions",
                json={
                    "model": "Qwen/Qwen2.5-Omni-3B",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Please transcribe this audio accurately:"
                                },
                                {
                                    "type": "audio_url",
                                    "audio_url": {
                                        "url": f"file://{audio_path}"
                                    }
                                }
                            ]
                        }
                    ],
                    "temperature": 0.1,  # Low temperature for accuracy
                    "max_tokens": 512
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"vLLM API error: {response.status} - {error_text}")

                result = await response.json()
                transcript = result["choices"][0]["message"]["content"]
                logger.info(f"Transcription completed: {len(transcript)} chars")
                return transcript.strip()

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            raise

    async def qa_with_context(
        self,
        lecture_id: str,
        query: str,
        history: List[Dict] = None
    ) -> str:
        """
        Q&A with lecture context using vLLM

        Uses conversation history to maintain context with lecture audio
        Phase 0 validated that audio persists via conversation history
        """
        try:
            logger.info(f"Processing Q&A for lecture {lecture_id}")

            session = await self._get_session()

            # Build messages with conversation history
            # Audio context is in the first message of the history
            messages = []

            # Add conversation history (includes lecture audio in first message)
            if history:
                messages.extend(history)

            # Add current query
            messages.append({
                "role": "user",
                "content": query
            })

            # Call vLLM chat completions
            async with session.post(
                f"{self.endpoint}/v1/chat/completions",
                json={
                    "model": "Qwen/Qwen2.5-Omni-3B",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1024
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"vLLM API error: {response.status} - {error_text}")

                result = await response.json()
                answer = result["choices"][0]["message"]["content"]
                logger.info(f"Q&A completed: {len(answer)} chars")
                return answer.strip()

        except Exception as e:
            logger.error(f"Error in Q&A: {e}", exc_info=True)
            raise
