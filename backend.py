"""
Backend service handling STT, LLM, and TTS integration
"""

import os
import asyncio
import json
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
import assemblyai as aai
from openai import OpenAI
from elevenlabs import ElevenLabs
import requests
from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE, MAX_CONVERSATION_HISTORY

# Load environment variables
load_dotenv()


class VoiceAssistantBackend:
    def __init__(self):
        # Initialize API clients
        self.assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        
        # Validate API keys
        if not self.assemblyai_key:
            raise ValueError("ASSEMBLYAI_API_KEY not found in environment variables")
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        if not self.elevenlabs_key:
            raise ValueError("ELEVENLABS_API_KEY not found in environment variables")
        
        # Setup clients
        aai.settings.api_key = self.assemblyai_key
        self.openai_client = OpenAI(api_key=self.openai_key)
        self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_key)
        
        # Conversation storage
        self.conversation_history: List[Dict] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize with system prompt
        self.conversation_history.append({
            "role": "system",
            "content": SYSTEM_PROMPT
        })
    
    def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio using AssemblyAI
        """
        try:
            # Save audio temporarily
            temp_file = f"temp_audio_{self.session_id}.wav"
            with open(temp_file, "wb") as f:
                f.write(audio_data)
            
            # Transcribe
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(temp_file)
            
            # Clean up
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            return transcript.text if transcript.text else ""
        
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
    
    def get_llm_response(self, user_message: str) -> str:
        """
        Get response from OpenAI
        """
        try:
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Prepare messages for API (without timestamps for API call)
            api_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in self.conversation_history
                if msg["role"] in ["system", "user", "assistant"]
            ]
            
            # Keep only recent history to avoid token limits
            if len(api_messages) > MAX_CONVERSATION_HISTORY + 1:  # +1 for system
                api_messages = [api_messages[0]] + api_messages[-(MAX_CONVERSATION_HISTORY):]
            
            # Call OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages,
                temperature=0.7,
                max_tokens=300
            )
            
            assistant_message = response.choices[0].message.content
            
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message,
                "timestamp": datetime.now().isoformat()
            })
            
            return assistant_message
        
        except Exception as e:
            print(f"LLM error: {e}")
            return "I apologize, but I'm having trouble processing that right now. Could you please try again?"
    
    def synthesize_speech(self, text: str) -> bytes:
        """
        Convert text to speech using ElevenLabs
        """
        try:
            # Generate audio
            audio = self.elevenlabs_client.text_to_speech.convert(
                voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel voice (default)
                text=text,
                model_id="eleven_turbo_v2_5"
            )
            
            # Collect audio chunks
            audio_data = b""
            for chunk in audio:
                audio_data += chunk
            
            return audio_data
        
        except Exception as e:
            print(f"TTS error: {e}")
            return b""
    
    def get_welcome_audio(self) -> bytes:
        """
        Generate welcome message audio
        """
        self.conversation_history.append({
            "role": "assistant",
            "content": WELCOME_MESSAGE,
            "timestamp": datetime.now().isoformat(),
            "type": "welcome"
        })
        return self.synthesize_speech(WELCOME_MESSAGE)
    
    def save_conversation(self) -> str:
        """
        Save conversation to JSON file
        """
        try:
            filename = f"conversation_{self.session_id}.json"
            
            # Prepare conversation data
            conversation_data = {
                "session_id": self.session_id,
                "start_time": self.conversation_history[1]["timestamp"] if len(self.conversation_history) > 1 else None,
                "end_time": datetime.now().isoformat(),
                "messages": [
                    msg for msg in self.conversation_history 
                    if msg["role"] != "system"  # Exclude system prompt from saved file
                ]
            }
            
            # Save to file
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
            
            print(f"Conversation saved to {filename}")
            return filename
        
        except Exception as e:
            print(f"Error saving conversation: {e}")
            return ""
    
    def process_user_audio(self, audio_data: bytes) -> tuple[str, bytes]:
        """
        Main processing pipeline: STT -> LLM -> TTS
        Returns: (text_response, audio_response)
        """
        # Step 1: Transcribe user audio
        user_text = self.transcribe_audio(audio_data)
        if not user_text:
            return "", b""
        
        print(f"User said: {user_text}")
        
        # Step 2: Get LLM response
        assistant_text = self.get_llm_response(user_text)
        print(f"Assistant: {assistant_text}")
        
        # Step 3: Convert to speech
        assistant_audio = self.synthesize_speech(assistant_text)
        
        return assistant_text, assistant_audio