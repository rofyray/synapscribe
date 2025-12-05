"""
QueryAgent - Main Q&A orchestration agent
Handles ASR, Q&A with context, TTS, and session management
"""

import os
import boto3
import logging
import json
import base64
from typing import AsyncGenerator, Dict, List
from datetime import datetime, timedelta
from utils.vllm_client import VLLMClient
from utils.gtts_client import GTTSClient

logger = logging.getLogger(__name__)


class QueryAgent:
    """
    QueryAgent handles:
    1. ASR of user query audio
    2. Q&A with lecture context using vLLM
    3. TTS of response
    4. Streaming audio chunks back to Lambda
    5. Session management and batch transcription
    """

    def __init__(self):
        # AWS clients
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')

        # AI service clients
        self.vllm = VLLMClient()
        self.gtts = GTTSClient()

        # Session memory (in-memory storage for Q&A pairs)
        self.session_memory = {}

        # Environment configuration
        self.s3_bucket = os.getenv('S3_BUCKET', 'synapscribe-audio-657177702657')
        self.dynamodb_table = os.getenv('DYNAMODB_TABLE', 'SynapScribe-Sessions')

        logger.info("QueryAgent initialized")

    async def process(self, payload: Dict) -> AsyncGenerator[bytes, None]:
        """
        Process Q&A query with streaming response

        Yields JSON lines:
        - {"type": "query_text", "text": "..."}
        - {"type": "answer_text", "text": "..."}
        - {"type": "audio_chunk", "data": "base64...", "index": 0}
        - {"type": "audio_complete"}
        - {"type": "error", "message": "..."}
        """
        session_id = payload.get("sessionId")
        lecture_id = payload.get("lectureId")
        query_audio_s3_key = payload.get("s3Key")
        connection_id = payload.get("connectionId")

        try:
            logger.info(f"Processing query for session {session_id}, lecture {lecture_id}")

            # Step 1: Download query audio from S3
            query_audio_path = f"/tmp/{session_id}_query.webm"
            self.s3.download_file(
                Bucket=self.s3_bucket,
                Key=query_audio_s3_key,
                Filename=query_audio_path
            )
            logger.info(f"Downloaded query audio to {query_audio_path}")

            # Step 2: ASR - Transcribe query using vLLM
            query_text = await self.vllm.transcribe_audio(query_audio_path)
            yield self._json_line({"type": "query_text", "text": query_text})
            logger.info(f"Query transcribed: {query_text[:100]}...")

            # Step 3: Load conversation history
            history = self._load_history(session_id, lecture_id, limit=10)
            logger.info(f"Loaded {len(history)} history messages")

            # Step 4: Q&A with vLLM using lecture context
            answer_text = await self.vllm.qa_with_context(
                lecture_id=lecture_id,
                query=query_text,
                history=history
            )
            yield self._json_line({"type": "answer_text", "text": answer_text})
            logger.info(f"Answer generated: {len(answer_text)} chars")

            # Step 5: TTS - Convert answer to speech
            audio_bytes = await self.gtts.text_to_speech(answer_text)
            logger.info(f"TTS completed: {len(audio_bytes)} bytes")

            # Step 6: Stream audio chunks
            chunk_size = 4096
            for i, chunk in enumerate(self._chunk_audio(audio_bytes, chunk_size)):
                encoded = base64.b64encode(chunk).decode('utf-8')
                yield self._json_line({
                    "type": "audio_chunk",
                    "data": encoded,
                    "index": i
                })

            # Step 7: Signal completion
            yield self._json_line({"type": "audio_complete"})
            logger.info("Query processing complete")

            # Step 8: Store Q&A in memory for batch transcription
            self._store_qa_in_memory(
                session_id=session_id,
                query_audio_s3_key=query_audio_s3_key,
                query_text=query_text,
                answer_text=answer_text,
                audio_bytes=audio_bytes
            )

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            yield self._json_line({"type": "error", "message": str(e)})

    async def end_session(self, payload: Dict) -> Dict:
        """
        Handle session end:
        1. Retrieve all Q&A pairs from memory
        2. Upload response audio to S3
        3. Save conversation to DynamoDB
        4. Clean up memory
        """
        session_id = payload.get("sessionId")
        lecture_id = payload.get("lectureId")

        try:
            logger.info(f"Ending session {session_id}")

            # Retrieve Q&A pairs from memory
            qa_pairs = self.session_memory.get(session_id, [])
            logger.info(f"Found {len(qa_pairs)} Q&A pairs")

            # Save conversation to DynamoDB
            conversation = []
            for turn, qa in enumerate(qa_pairs, start=1):
                # Upload response audio to S3
                response_s3_key = f"responses/{session_id}/response-{turn}.mp3"
                self.s3.put_object(
                    Bucket=self.s3_bucket,
                    Key=response_s3_key,
                    Body=qa['response_audio'],
                    ContentType='audio/mpeg'
                )
                logger.info(f"Uploaded response audio: {response_s3_key}")

                conversation.append({
                    "turn": turn,
                    "queryText": qa['query_text'],
                    "responseText": qa['response_text'],
                    "queryAudio": qa['query_audio_s3_key'],
                    "responseAudio": response_s3_key,
                    "timestamp": qa['timestamp']
                })

            # Save to DynamoDB
            table = self.dynamodb.Table(self.dynamodb_table)
            expires_at = int((datetime.now() + timedelta(days=7)).timestamp())

            table.put_item(Item={
                "sessionId": session_id,
                "lectureId": lecture_id,
                "conversation": conversation,
                "totalTurns": len(conversation),
                "createdAt": datetime.now().isoformat(),
                "expiresAt": expires_at
            })
            logger.info(f"Saved conversation to DynamoDB")

            # Clean up memory
            if session_id in self.session_memory:
                del self.session_memory[session_id]

            return {
                "status": "session_ended",
                "turns": len(conversation),
                "sessionId": session_id
            }

        except Exception as e:
            logger.error(f"Error ending session: {e}", exc_info=True)
            raise

    def _json_line(self, data: dict) -> bytes:
        """Convert dict to JSON line (newline-delimited JSON)"""
        return (json.dumps(data) + "\n").encode('utf-8')

    def _chunk_audio(self, audio_bytes: bytes, chunk_size: int):
        """Yield audio chunks of specified size"""
        for i in range(0, len(audio_bytes), chunk_size):
            yield audio_bytes[i:i + chunk_size]

    def _load_history(self, session_id: str, lecture_id: str, limit: int = 10) -> List[Dict]:
        """
        Load conversation history from DynamoDB

        Returns messages in vLLM chat format with audio context
        """
        try:
            table = self.dynamodb.Table(self.dynamodb_table)
            response = table.get_item(
                Key={
                    "sessionId": session_id,
                    "lectureId": lecture_id
                }
            )

            if 'Item' not in response:
                logger.info("No existing conversation history found")
                # Return empty history for now
                # TODO: Load lecture audio into first message when lecture context loading is implemented
                return []

            # Get conversation history
            conversation = response['Item'].get('conversation', [])

            # Convert to vLLM chat format (last N turns)
            messages = []
            for turn in conversation[-limit:]:
                messages.append({
                    "role": "user",
                    "content": turn['queryText']
                })
                messages.append({
                    "role": "assistant",
                    "content": turn['responseText']
                })

            logger.info(f"Loaded {len(messages)} messages from history")
            return messages

        except Exception as e:
            logger.error(f"Error loading history: {e}", exc_info=True)
            return []

    def _store_qa_in_memory(
        self,
        session_id: str,
        query_audio_s3_key: str,
        query_text: str,
        answer_text: str,
        audio_bytes: bytes
    ):
        """Store Q&A pair in memory for later batch save"""
        if session_id not in self.session_memory:
            self.session_memory[session_id] = []

        self.session_memory[session_id].append({
            "query_audio_s3_key": query_audio_s3_key,
            "query_text": query_text,
            "response_text": answer_text,
            "response_audio": audio_bytes,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"Stored Q&A pair in memory for session {session_id}")
