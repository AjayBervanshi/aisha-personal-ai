import logging
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_trending_topics(api_key, region_code):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.videos().list(
            part="id,snippet",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=10
        )
        response = request.execute()
        trending_topics = []
        for item in response['items']:
            trending_topics.append(item['snippet']['title'])
        return trending_topics
    except HttpError as e:
        logger.error(f"Error fetching trending topics: {e}")
        return []

def get_popular_videos(api_key, region_code):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.videos().list(
            part="id,snippet",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=10
        )
        response = request.execute()
        popular_videos = []
        for item in response['items']:
            popular_videos.append({
                'id': item['id'],
                'title': item['snippet']['title'],
                'description': item['snippet']['description']
            })
        return popular_videos
    except HttpError as e:
        logger.error(f"Error fetching popular videos: {e}")
        return []

def get_relevant_keywords(api_key, topic):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.search().list(
            part="id,snippet",
            q=topic,
            type="video",
            maxResults=10
        )
        response = request.execute()
        relevant_keywords = []
        for item in response['items']:
            relevant_keywords.append(item['snippet']['title'])
        return relevant_keywords
    except HttpError as e:
        logger.error(f"Error fetching relevant keywords: {e}")
        return []

def preprocess_data(trending_topics, popular_videos, relevant_keywords):
    try:
        data = {
            'trending_topics': trending_topics,
            'popular_videos': popular_videos,
            'relevant_keywords': relevant_keywords
        }
        return data
    except Exception as e:
        logger.error(f"Error preprocessing data: {e}")
        return {}

def load_data_to_bigquery(data, project_id, dataset_id, table_id):
    try:
        client = bigquery.Client(project=project_id)
        table_ref = client.dataset(dataset_id).table(table_id)
        table = client.get_table(table_ref)
        errors = client.insert_rows(table, [data])
        if errors:
            logger.error(f"Error loading data to BigQuery: {errors}")
        else:
            logger.info("Data loaded to BigQuery successfully")
    except Exception as e:
        logger.error(f"Error loading data to BigQuery: {e}")

def auto_youtube_trend_aggreg(api_key, region_code, project_id, dataset_id, table_id):
    """
    This module fetches trending topics, popular videos, and relevant keywords from YouTube Data API.
    It preprocesses and structures this data, making it readily available for consumption by agents like the "Story Researcher" to improve the quality and relevance of trend analysis.

    Args:
        api_key (str): YouTube Data API key
        region_code (str): Region code for trending topics and popular videos
        project_id (str): Google Cloud project ID
        dataset_id (str): BigQuery dataset ID
        table_id (str): BigQuery table ID

    Returns:
        None
    """
    trending_topics = get_trending_topics(api_key, region_code)
    popular_videos = get_popular_videos(api_key, region_code)
    relevant_keywords = get_relevant_keywords(api_key, trending_topics[0])
    data = preprocess_data(trending_topics, popular_videos, relevant_keywords)
    load_data_to_bigquery(data, project_id, dataset_id, table_id)

if __name__ == "__main__":
    api_key = os.environ.get('YOUTUBE_API_KEY')
    region_code = 'US'
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    dataset_id = 'youtube_data'
    table_id = 'trending_topics'
    auto_youtube_trend_aggreg(api_key, region_code, project_id, dataset_id, table_id)