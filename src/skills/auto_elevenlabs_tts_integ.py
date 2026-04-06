import os
import logging
from typing import Optional, List, Dict, Any

from elevenlabs import generate, set_api_key, voices, user
from elevenlabs.client import ElevenLabs
from elevenlabs.types import Voice, VoiceSettings
from elevenlabs.api import ElevenLabsError

# Configure logging for the module
logger = logging.getLogger(__name__)
# Basic configuration for when the module is run directly.
# In a larger application, the root logger would be configured elsewhere.
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class ElevenLabsTTSIntegrator:
    """
    Encapsulates all ElevenLabs Text-to-Speech (TTS) API interactions.

    This class provides a clean interface for `voice_engine.py` to utilize
    ElevenLabs TTS capabilities, handling API key management, character quota
    checks, text synthesis, audio data retrieval, and specific ElevenLabs
    error handling.

    It expects the ElevenLabs API key to be provided during instantiation or
    set as an environment variable named `ELEVENLABS_API_KEY`.

    Attributes:
        _api_key (str): The ElevenLabs API key used for authentication.
        _client (ElevenLabs): The ElevenLabs client instance for API interactions.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the ElevenLabsTTSIntegrator.

        Args:
            api_key (Optional[str]): The ElevenLabs API key. If None, the key
                                     will be loaded from the ELEVENLABS_API_KEY
                                     environment variable.

        Raises:
            ValueError: If no API key is provided and the environment variable
                        is not set.
        """
        self._api_key = api_key or os.getenv("ELEVENLABS_API_KEY")

        if not self._api_key:
            logger.error("ElevenLabs API key not found. Please provide it or set the ELEVENLABS_API_KEY environment variable.")
            raise ValueError(
                "ElevenLabs API key is required. "
                "Set it as an environment variable 'ELEVENLABS_API_KEY' "
                "or pass it directly to the constructor."
            )

        # Set the API key globally for the elevenlabs library functions
        set_api_key(self._api_key)
        # Initialize the client for more explicit control and future features
        self._client = ElevenLabs(api_key=self._api_key)
        logger.info("ElevenLabsTTSIntegrator initialized successfully.")

    def _handle_elevenlabs_error(self, e: ElevenLabsError, action: str) -> None:
        """
        Internal helper to log ElevenLabs specific errors.
        """
        logger.error(f"ElevenLabs API error during {action}: {e}")
        logger.debug(f"ElevenLabs error details: status_code={e.status_code}, detail={e.detail}")
        # Specific error handling can be added here, e.g., for quota exceeded
        if e.status_code == 401:
            logger.error("Authentication failed. Please check your ElevenLabs API key.")
        elif e.status_code == 402:
            logger.warning("ElevenLabs character quota exceeded or subscription issue.")
        elif e.status_code == 400 and "voice" in str(e.detail).lower():
            logger.error(f"Invalid voice ID or voice settings provided: {e.detail}")
        elif e.status_code == 400 and "model" in str(e.detail).lower():
            logger.error(f"Invalid model ID provided: {e.detail}")

    def synthesize(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        output_format: str = "mp3_44100_128",
        voice_settings: Optional[VoiceSettings] = None
    ) -> Optional[bytes]:
        """
        Synthesizes text into speech using the ElevenLabs API.

        Args:
            text (str): The text to be synthesized.
            voice_id (str): The ID of the voice to use for synthesis.
            model_id (str): The ID of the model to use (e.g., "eleven_multilingual_v2").
                            Defaults to "eleven_multilingual_v2".
            output_format (str): The audio output format (e.g., "mp3_44100_128").
                                 Defaults to "mp3_44100_128".
            voice_settings (Optional[VoiceSettings]): Optional voice settings to
                                                      override default voice parameters.

        Returns:
            Optional[bytes]: The audio data as bytes if successful, None otherwise.
        """
        if not text:
            logger.warning("Attempted to synthesize empty text.")
            return None
        if not voice_id:
            logger.error("Voice ID cannot be empty for synthesis.")
            return None

        logger.info(f"Synthesizing text with voice_id='{voice_id}', model_id='{model_id}', "
                    f"output_format='{output_format}'. Text length: {len(text)} characters.")
        logger.debug(f"Text to synthesize: '{text[:100]}...'") # Log first 100 chars

        try:
            audio = generate(
                text=text,
                voice=voice_id,
                model=model_id,
                output_format=output_format,
                voice_settings=voice_settings
            )
            logger.info(f"Successfully synthesized audio for voice_id='{voice_id}'. "
                        f"Audio data size: {len(audio)} bytes.")
            return audio
        except ElevenLabsError as e:
            self._handle_elevenlabs_error(e, "text synthesis")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during text synthesis: {e}", exc_info=True)
            return None

    def get_character_quota(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the current character usage and subscription details from ElevenLabs.

        This can be used to check remaining character quota.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing subscription details
                                      (e.g., 'character_limit', 'character_used',
                                      'can_do_text_to_speech'), or None if an error occurs.
        """
        logger.info("Attempting to retrieve ElevenLabs character quota information.")
        try:
            subscription_info = user.get_subscription()
            quota_data = {
                "character_limit": subscription_info.character_limit,
                "character_used": subscription_info.character_used,
                "can_do_text_to_speech": subscription_info.can_do_text_to_speech,
                "tier": subscription_info.tier,
                "next_renewal_unix": subscription_info.next_character_reset_unix,
            }
            logger.info(f"ElevenLabs quota: Used {quota_data['character_used']}/{quota_data['character_limit']} characters.")
            return quota_data
        except ElevenLabsError as e:
            self._handle_elevenlabs_error(e, "character quota retrieval")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while getting character quota: {e}", exc_info=True)
            return None

    def list_voices(self) -> Optional[List[Dict[str, Any]]]:
        """
        Lists available voices from the ElevenLabs API.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of dictionaries, each representing
                                            a voice with its ID, name, and description,
                                            or None if an error occurs.
        """
        logger.info("Attempting to list available ElevenLabs voices.")
        try:
            available_voices: List[Voice] = voices.get_all()
            voice_list = [
                {
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "category": voice.category,
                    "description": voice.description,
                    "labels": voice.labels,
                    "settings": voice.settings.dict() if voice.settings else None # Convert VoiceSettings to dict
                }
                for voice in available_voices
            ]
            logger.info(f"Successfully retrieved {len(voice_list)} ElevenLabs voices.")
            return voice_list
        except ElevenLabsError as e:
            self._handle_elevenlabs_error(e, "listing voices")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while listing voices: {e}", exc_info=True)
            return None


if __name__ == "__main__":
    # Configure logging for the __main__ block
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Running ElevenLabsTTSIntegrator __main__ test.")

    # --- Test 1: Initialization without API key (should fail) ---
    logger.info("\n--- Test 1: Initialization without API key (expected to fail if env var not set) ---")
    original_env_key = os.getenv("ELEVENLABS_API_KEY")
    if original_env_key:
        del os.environ["ELEVENLABS_API_KEY"] # Temporarily unset for this test

    try:
        integrator_no_key = ElevenLabsTTSIntegrator()
    except ValueError as e:
        logger.info(f"Caught expected error: {e}")
    finally:
        if original_env_key:
            os.environ["ELEVENLABS_API_KEY"] = original_env_key # Restore env var

    # --- Test 2: Initialization with API key (from env or direct) ---
    logger.info("\n--- Test 2: Initialization with API key ---")
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    if not elevenlabs_api_key:
        logger.warning("ELEVENLABS_API_KEY environment variable not set. "
                       "Please set it to run the full __main__ test.")
        logger.warning("Skipping further tests as API key is missing.")
    else:
        try:
            integrator = ElevenLabsTTSIntegrator(api_key=elevenlabs_api_key)

            # --- Test 3: List Voices ---
            logger.info("\n--- Test 3: Listing voices ---")
            voices_list = integrator.list_voices()
            if voices_list:
                logger.info(f"Found {len(voices_list)} voices. First 3 voices:")
                for i, voice in enumerate(voices_list[:3]):
                    logger.info(f"  Voice {i+1}: ID='{voice['voice_id']}', Name='{voice['name']}'")
                # Pick a default voice for synthesis
                test_voice_id = voices_list[0]['voice_id'] if voices_list else "21m00Tzpb8x4TrYxZzP0" # Rachel
                logger.info(f"Using voice ID: {test_voice_id} for synthesis test.")
            else:
                logger.error("Failed to list voices.")
                test_voice_id = "21m00Tzpb8x4TrYxZzP0" # Fallback to Rachel if listing fails

            # --- Test 4: Get Character Quota ---
            logger.info("\n--- Test 4: Getting character quota ---")
            quota_info = integrator.get_character_quota()
            if quota_info:
                logger.info(f"Quota Info: Used {quota_info['character_used']}/{quota_info['character_limit']} characters. "
                            f"Tier: {quota_info['tier']}. TTS enabled: {quota_info['can_do_text_to_speech']}")
            else:
                logger.error("Failed to retrieve character quota.")

            # --- Test 5: Synthesize Text ---
            logger.info("\n--- Test 5: Synthesizing text ---")
            sample_text = "Hello Aisha AI, this is a test of the ElevenLabs Text-to-Speech integration module. I hope it works perfectly!"
            audio_data = integrator.synthesize(text=sample_text, voice_id=test_voice_id)

            if audio_data:
                output_filename = "elevenlabs_test_output.mp3"
                with open(output_filename, "wb") as f:
                    f.write(audio_data)
                logger.info(f"Successfully synthesized audio and saved to '{output_filename}'.")
            else:
                logger.error("Failed to synthesize audio.")

            # --- Test 6: Synthesize with invalid voice ID (expected to fail) ---
            logger.info("\n--- Test 6: Synthesizing with invalid voice ID (expected to fail) ---")
            invalid_voice_id = "invalid_voice_id_123"
            audio_data_invalid_voice = integrator.synthesize(text="This should fail.", voice_id=invalid_voice_id)
            if audio_data_invalid_voice is None:
                logger.info("Successfully handled synthesis failure for invalid voice ID.")
            else:
                logger.error("Synthesis with invalid voice ID unexpectedly succeeded.")

            # --- Test 7: Synthesize with empty text (expected to return None) ---
            logger.info("\n--- Test 7: Synthesizing with empty text (expected to return None) ---")
            audio_data_empty_text = integrator.synthesize(text="", voice_id=test_voice_id)
            if audio_data_empty_text is None:
                logger.info("Successfully handled synthesis with empty text.")
            else:
                logger.error("Synthesis with empty text unexpectedly returned audio.")

        except Exception as e:
            logger.critical(f"An unhandled exception occurred during __main__ tests: {e}", exc_info=True)

    logger.info("ElevenLabsTTSIntegrator __main__ test finished.")