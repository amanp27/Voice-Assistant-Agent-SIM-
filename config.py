"""
Performance and configuration settings for the voice assistant
"""

# OpenAI Configuration
OPENAI_MODEL = "gpt-4o-mini"  # Fast model
OPENAI_MAX_TOKENS = 150  # Shorter responses = faster
OPENAI_TEMPERATURE = 0.7

# ElevenLabs Configuration
ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
ELEVENLABS_MODEL = "eleven_turbo_v2_5"  # Fastest TTS model
ELEVENLABS_OPTIMIZE_LATENCY = 4  # 0-4, 4 is fastest

# AssemblyAI Configuration
ASSEMBLYAI_LANGUAGE_CODE = "en"  # English only for faster processing

# Performance Settings
ENABLE_AUDIO_COMPRESSION = True  # Compress audio for faster transfer
AUDIO_SAMPLE_RATE = 16000  # Lower = faster (16kHz is good for speech)

# If you want even faster responses, you can:
# 1. Use "gpt-3.5-turbo" instead of "gpt-4o-mini" (faster but less accurate)
# 2. Reduce OPENAI_MAX_TOKENS to 100
# 3. Use a smaller ElevenLabs voice model (if available)