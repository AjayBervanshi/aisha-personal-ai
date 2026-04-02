import logging
import re
from typing import Dict, Optional
from src.core import Channel, YouTubeCrewAgent

logger = logging.getLogger(__name__)

def validate_channel(channel_name_or_id: str) -> Optional[Dict]:
    """
    Validates a YouTube channel by name or ID and returns a standardized channel object.

    This function checks if the channel exists, if the name is valid, and if the channel is properly configured.
    It handles cases where the input data is invalid or missing and returns None in such cases.

    Args:
        channel_name_or_id (str): The name or ID of the YouTube channel to validate.

    Returns:
        Optional[Dict]: A dictionary representing the validated channel object, or None if validation fails.
    """

    try:
        # Check if the input is a valid channel ID
        if re.match(r'^[a-zA-Z0-9_-]{1,24}$', channel_name_or_id):
            channel_id = channel_name_or_id
            channel_name = YouTubeCrewAgent.get_channel_name(channel_id)
            if channel_name is None:
                logger.error(f"Channel with ID {channel_id} does not exist")
                return None
        # Check if the input is a valid channel name
        elif re.match(r'^[a-zA-Z0-9\s]+$', channel_name_or_id):
            channel_name = channel_name_or_id
            channel_id = YouTubeCrewAgent.get_channel_id(channel_name)
            if channel_id is None:
                logger.error(f"Channel with name {channel_name} does not exist")
                return None
        else:
            logger.error(f"Invalid channel name or ID: {channel_name_or_id}")
            return None

        # Check if the channel is properly configured
        if not YouTubeCrewAgent.is_channel_configured(channel_id):
            logger.error(f"Channel with ID {channel_id} is not properly configured")
            return None

        # Create and return the standardized channel object
        channel = Channel(channel_id, channel_name)
        return channel.to_dict()

    except Exception as e:
        logger.error(f"Error validating channel: {e}")
        return None

if __name__ == "__main__":
    channel_name_or_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    validated_channel = validate_channel(channel_name_or_id)
    print(validated_channel)