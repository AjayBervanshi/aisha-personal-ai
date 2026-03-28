import logging
import os
import requests
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_api_key():
    try:
        api_key = os.environ.get('ELEVENLABS_API_KEY')
        if not api_key:
            logging.error('ElevenLabs API key not found in environment variables')
            raise Exception('ElevenLabs API key not found')
        return api_key
    except Exception as e:
        logging.error(f'Failed to retrieve ElevenLabs API key: {str(e)}')
        raise

def check_quota(api_key):
    try:
        response = requests.get(f'https://api.elevenlabs.io/v1/quota', headers={'Authorization': f'Bearer {api_key}'})
        response.raise_for_status()
        quota = response.json()['quota']
        logging.info(f'Remaining quota: {quota}')
        return quota
    except requests.exceptions.RequestException as e:
        logging.error(f'Failed to check ElevenLabs quota: {str(e)}')
        raise

def generate_audio(api_key, text, voice):
    try:
        quota = check_quota(api_key)
        if quota <= 0:
            logging.error('Insufficient quota to generate audio')
            raise Exception('Insufficient quota')
        response = requests.post(f'https://api.elevenlabs.io/v1/text-to-speech', headers={'Authorization': f'Bearer {api_key}'}, json={'text': text, 'voice': voice})
        response.raise_for_status()
        audio_url = response.json()['url']
        logging.info(f'Generated audio: {audio_url}')
        return audio_url
    except Exception as e:
        logging.error(f'Failed to generate audio using ElevenLabs API: {str(e)}')
        raise

def __main__():
    api_key = get_api_key()
    quota = check_quota(api_key)
    text = 'Hello, world!'
    voice = 'en-US'
    audio_url = generate_audio(api_key, text, voice)
    print(f'Generated audio URL: {audio_url}')

if __name__ == '__main__':
    __main__()