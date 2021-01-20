from typing import List, Union
from asyncio import sleep

import pandas as pd
from fastapi import FastAPI, status, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from data import load_users, load_parties, load_coalitions, \
    load_topics_distributions, load_sentiment_distributions, \
    load_words_per_topic, load_words_counts, get_db_engine
from models import *
from response import TopicDistribution, WordsCounts, ProfileImage
from twitter import get_twitter_api_instance, get_profile_photo

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"])

users = load_users()
parties = load_parties()
coalitions = load_coalitions()

topics_dist = load_topics_distributions()
sentiment_dist = load_sentiment_distributions()
words_per_topic = load_words_per_topic()
words_counts = load_words_counts()

twitterAPI = get_twitter_api_instance()

db_engine = get_db_engine()


def get_tweets_by_column(
        column_name: str,
        column_value: Union[str, int],
        limit: int = 5,
        sentiment: Optional[str] = None,
        topic: Optional[int] = None
):
    selected = pd.read_sql(
        f"SELECT * FROM tweets WHERE {column_name} = \"{column_value}\"",
        db_engine
    )

    if sentiment is not None:
        selected = selected[selected['sentiment'] == sentiment]

    if topic is not None:
        selected = selected[selected['topic'] == topic]

    if len(selected) < limit:
        return selected
    elif topic is None:
        return selected.sample(limit)
    else:
        return selected.nlargest(limit, 'topic_proba')


def tweets_from_rows(row: pd.Series) -> Tweet:
    return Tweet(
        tweet_id=row['id'],
        twitter_link=row['link'],
        username=row['username'],
        tweet_text=row['tweet'],
        topic=row['topic'],
        topic_proba=row['topic_proba'],
        sentiment=row['sentiment']
    )


@app.get("/user", response_model=List[User])
async def get_all_users() -> List[User]:
    return users


@app.get("/user/{username}", response_model=User)
async def get_user(username: str) -> User:
    user = next((user for user in users if user.username == username), None)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found')
    else:
        return user


@app.get("/user/{username}/topic", response_model=List[TopicDistribution])
async def get_topics_by_username(username: str):
    topics_per_user = topics_dist['per_user']

    if username not in topics_per_user.keys():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found')
    else:
        return topics_per_user[username]


@app.get("/user/{username}/sentiment")
async def get_sentiment_by_username(username: str):
    sentiment_per_user = sentiment_dist['per_user']

    if username not in sentiment_per_user.keys():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found')
    else:
        return sentiment_per_user[username]


@app.get("/user/{username}/word", response_model=List[WordsCounts])
async def get_words_by_username(username: str, limit: int = 100):
    words_per_user = words_counts['per_user']

    if username not in words_per_user.keys():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found')
    elif limit < 1:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail='Limit must be positive integer'
        )
    else:
        return words_per_user[username][:limit]


@app.get("/user/{username}/tweets", response_model=List[Tweet])
async def get_tweets_by_username(
        username: str,
        limit: int = 5,
        topic: Optional[int] = None,
        sentiment: Optional[str] = None
) -> List[Tweet]:
    user = next((user for user in users if user.username == username), None)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )
    else:
        user_tweets = get_tweets_by_column(
            column_name='username',
            column_value=username,
            limit=limit,
            topic=topic,
            sentiment=sentiment
        )
        return user_tweets.apply(tweets_from_rows, axis=1).tolist() if len(
            user_tweets) > 0 else []


@app.get("/user/{username}/photo", response_model=ProfileImage)
async def get_user_photo(username: str):
    user = next((user for user in users if user.username == username), None)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )
    else:
        url = get_profile_photo(twitterAPI, username)

        return {"url": url}


@app.get("/party", response_model=List[Party])
async def get_all_parties() -> List[Party]:
    return parties


@app.get("/party/{party_id}", response_model=Party)
async def get_party(party_id: int) -> Party:
    party = next((party for party in parties if party.party_id == party_id),
                 None)

    if party is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Party not found')
    else:
        return party


@app.get("/party/{party_id}/topic", response_model=List[TopicDistribution])
async def get_topics_by_party(party_id: int):
    topics_per_party = topics_dist['per_party']

    party = next((party for party in parties if party.party_id == party_id),
                 None)

    if party is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Party not found')
    else:
        return topics_per_party[party.name]


@app.get("/party/{party_id}/sentiment")
async def get_sentiment_by_party(party_id: int):
    sentiment_per_party = sentiment_dist['per_party']

    party = next((party for party in parties if party.party_id == party_id),
                 None)

    if party is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Party not found')
    else:
        return sentiment_per_party[party.name]


@app.get("/party/{party_id}/word", response_model=List[WordsCounts])
async def get_words_by_party(party_id: int, limit: int = 100):
    words_per_party = words_counts['per_party']

    party = next((party for party in parties if party.party_id == party_id),
                 None)

    if party is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Party not found')
    elif limit < 1:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail='Limit must be positive integer'
        )
    else:
        return words_per_party[party.name][:limit]


@app.get("/party/{party_id}/tweets", response_model=List[Tweet])
async def get_tweets_by_party(
        party_id: int,
        limit: int = 5,
        topic: Optional[int] = None,
        sentiment: Optional[str] = None
) -> List[Tweet]:
    party = next((party for party in parties if party.party_id == party_id),
                 None)

    if party is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )
    else:
        party_tweets = get_tweets_by_column(
            column_name='party',
            column_value=party.name,
            limit=limit,
            topic=topic,
            sentiment=sentiment
        )
        return party_tweets.apply(tweets_from_rows, axis=1).tolist() if len(
            party_tweets) > 0 else []


@app.get("/coalition", response_model=List[Coalition])
async def get_all_coalitions() -> List[Coalition]:
    return coalitions


@app.get("/coalition/{coalition_id}", response_model=Coalition)
async def get_coalition(coalition_id: int) -> Coalition:
    coalition = next((coalition for coalition in coalitions if
                      coalition.coalition_id == coalition_id), None)

    if coalition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Coalition not found')
    else:
        return coalition


@app.get("/coalition/{coalition_id}/topic",
         response_model=List[TopicDistribution])
async def get_topics_by_coalition(coalition_id: int):
    topics_per_coalition = topics_dist['per_coalition']

    coalition = next((coalition for coalition in coalitions if
                      coalition.coalition_id == coalition_id), None)

    if coalition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Party not found')
    else:
        return topics_per_coalition[coalition.name]


@app.get("/coalition/{coalition_id}/sentiment")
async def get_sentiment_by_coalition(coalition_id: int):
    sentiment_per_coalition = sentiment_dist['per_coalition']

    coalition = next((coalition for coalition in coalitions if
                      coalition.coalition_id == coalition_id), None)

    if coalition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Party not found')
    else:
        return sentiment_per_coalition[coalition.name]


@app.get("/coalition/{coalition_id}/word", response_model=List[WordsCounts])
async def get_words_by_coalition(coalition_id: int, limit: int = 100):
    words_per_coalition = words_counts['per_coalition']

    coalition = next((coalition for coalition in coalitions if
                      coalition.coalition_id == coalition_id), None)

    if coalition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Party not found')
    elif limit < 1:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail='Limit must be positive integer'
        )
    else:
        return words_per_coalition[coalition.name][:limit]


@app.get("/coalition/{coalition_id}/tweets", response_model=List[Tweet])
async def get_tweets_by_coalition(
        coalition_id: int,
        limit: int = 5,
        topic: Optional[int] = None,
        sentiment: Optional[str] = None
) -> List[Tweet]:
    coalition = next((coalition for coalition in coalitions if
                      coalition.coalition_id == coalition_id), None)

    if coalition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )
    else:
        coalition_tweets = get_tweets_by_column(
            column_name='coalition',
            column_value=coalition.name,
            limit=limit,
            topic=topic,
            sentiment=sentiment
        )
        return coalition_tweets.apply(tweets_from_rows, axis=1).tolist() if len(
            coalition_tweets) > 0 else []


@app.get("/topic")
async def get_topics() -> List[int]:
    topics = words_per_topic.keys()

    return list(topics)


@app.get("/topic/{topic_id}/sentiment")
async def get_sentiment_by_topic(topic_id: int):
    sentiment_per_topic = sentiment_dist['per_topic']

    if topic_id not in sentiment_per_topic.keys():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found')
    else:
        return sentiment_per_topic[topic_id]


@app.get("/topic/{topic_id}/word", response_model=List[WordsCounts])
async def get_words_by_topic(topic_id: int, limit: int = 100):
    if topic_id not in words_per_topic.keys():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found')
    elif limit < 1:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail='Limit must be positive integer'
        )
    else:
        return words_per_topic[topic_id][:limit]


@app.get("/topic/{topic_id}/tweets", response_model=List[Tweet])
async def get_tweets_by_topic(topic_id: int, limit: int = 5):
    if topic_id not in words_per_topic.keys():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found')
    elif limit < 1:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail='Limit must be positive integer'
        )
    else:
        topic_tweets = get_tweets_by_column(
            column_name='topic',
            column_value=topic_id,
            topic=topic_id,
            limit=limit
        )
        return topic_tweets.apply(tweets_from_rows, axis=1).tolist() if len(
            topic_tweets) > 0 else []


@app.websocket("/test_ws")
async def test_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Ala ma kota")
    await sleep(3)
    await websocket.send_text("Ale jej zdechl")


@app.websocket("/new")
async def analyze_new_username(websocket: WebSocket):
    pass
