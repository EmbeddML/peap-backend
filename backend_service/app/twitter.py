import os

from TwitterAPI import TwitterAPI

CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
ACCESS_TOKEN_KEY = os.getenv('ACCESS_TOKEN_KEY')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')


def get_twitter_api_instance() -> TwitterAPI:
    api = TwitterAPI(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET)

    return api


def get_profile_photo(api: TwitterAPI, username: str) -> str:
    user_data = api.request('users/show', {
        'screen_name': f"{username}"
    }).json()
    url = user_data['profile_image_url_https'].replace("_normal", "")

    return url
