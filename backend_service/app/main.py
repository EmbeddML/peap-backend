import asyncio
import logging
from typing import List, Dict, Union

import pandas as pd
from celery import Celery, signature, chain
from fastapi import FastAPI, status, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

import celery_conf
from data import load_users, load_parties, load_coalitions, \
    load_topics_distributions, load_sentiment_distributions, \
    load_words_per_topic, load_words_counts, get_db_engine
from exceptions import WrongUsernameException, NoTweetsLeftException
from models import *
from response import TopicDistribution, WordsCounts, ProfileImage
from settings import STATUS_OK, STATUS_ERROR
from twitter import get_twitter_api_instance, get_profile_photo

app = FastAPI()

celery_app = Celery()
celery_app.config_from_object(celery_conf)

app.add_middleware(CORSMiddleware, allow_origins=["*"])

users = load_users()
clients_users = []
parties = load_parties()
coalitions = load_coalitions()

topics_dist = load_topics_distributions()
clients_topic_dist = {}
sentiment_dist = load_sentiment_distributions()
client_sentiment_dist = {}
words_per_topic = load_words_per_topic()
words_counts = load_words_counts()
clients_words_counts = {}

twitterAPI = get_twitter_api_instance()

db_engine = get_db_engine()


def get_logger(mod_name):
    logger = logging.getLogger(mod_name)
    logger.propagate = False
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


LOG = get_logger('BACKEND')


async def get_tweets_by_column(
        column_name: str,
        column_value: Union[str, int],
        limit: int = 5,
        sentiment: Optional[str] = None,
        topic: Optional[int] = None,
        table: str = 'tweets'
):
    selected = pd.read_sql(
        f"SELECT DISTINCT * FROM {table} WHERE {column_name} = \"{column_value}\"",
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
    client_user = next((user for user in clients_users
                        if user.username == username.lower()), None)

    if user is None and client_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found')
    else:
        return user if user is not None else client_user


@app.get("/user/{username}/topic", response_model=List[TopicDistribution])
async def get_topics_by_username(username: str):

    topics_per_user = topics_dist['per_user']

    if username not in topics_per_user.keys():
        if username.lower() not in clients_topic_dist.keys():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found')
        else:
            return clients_topic_dist[username.lower()]
    else:
        return topics_per_user[username]


@app.get("/user/{username}/sentiment")
async def get_sentiment_by_username(username: str):
    sentiment_per_user = sentiment_dist['per_user']

    if username not in sentiment_per_user.keys():
        if username.lower() not in client_sentiment_dist.keys():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found')
        else:
            return client_sentiment_dist[username.lower()]
    else:
        return sentiment_per_user[username]


@app.get("/user/{username}/word", response_model=List[WordsCounts])
async def get_words_by_username(username: str, limit: int = 100):
    words_per_user = words_counts['per_user']

    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail='Limit must be positive integer'
        )
    elif username not in words_per_user.keys():
        if username.lower() not in clients_words_counts.keys():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found')
        else:
            return clients_words_counts[username.lower()][:limit]
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
    client_user = next((user for user in clients_users
                        if user.username == username.lower()), None)

    if user is None:
        if client_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )
        else:
            user_tweets = await get_tweets_by_column(
                column_name='username',
                column_value=username.lower(),
                limit=limit,
                topic=topic,
                sentiment=sentiment,
                table='clients_tweets'
            )
            return user_tweets.apply(tweets_from_rows, axis=1).tolist() if len(
                user_tweets) > 0 else []
    else:
        user_tweets = await get_tweets_by_column(
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
    client_user = next((user for user in clients_users
                        if user.username == username.lower()), None)

    if user is None and client_user is None:
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
        party_tweets = await get_tweets_by_column(
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
        coalition_tweets = await get_tweets_by_column(
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
        topic_tweets = await get_tweets_by_column(
            column_name='topic',
            column_value=topic_id,
            topic=topic_id,
            limit=limit
        )
        return topic_tweets.apply(tweets_from_rows, axis=1).tolist() if len(
            topic_tweets) > 0 else []


def get_response(curr_status: str, text: str) -> Dict[str, str]:
    return {
        "status": curr_status,
        "text": text
    }


async def download_tweets(username: str) -> pd.DataFrame:
    tweets_getting = signature('get_tweets', args=(username,),
                               options={'queue': 'tweets'}).delay()

    while not tweets_getting.ready():
        await asyncio.sleep(2)

    if tweets_getting.failed():
        raise WrongUsernameException()
    else:
        return tweets_getting.get()


async def analyze(tweets: pd.DataFrame):
    cleaning = signature('clean', args=(tweets,),
                         options={'queue': 'cleaning'}).delay()

    while not cleaning.ready():
        await asyncio.sleep(1)

    cleaned = cleaning.get()

    if len(cleaned) == 0:
        raise NoTweetsLeftException()

    await asyncio.sleep(1)

    lemmatization = chain(
        signature('lemmatize', args=(cleaned,), options={'queue': 'cleaning'}),
        signature('stopwords', options={'queue': 'cleaning'})
    ).delay()

    emoji_removal = signature('emoji', args=(cleaned,),
                              options={'queue': 'cleaning'}).delay()

    emb_calc = signature('embedding', args=(cleaned, ),
                         options={'queue': 'embedding'}).delay()

    while not emoji_removal.ready():
        await asyncio.sleep(1)

    emojied = emoji_removal.get()

    sentiment = signature('sentiment', args=(emojied, ),
                          options={'queue': 'processing'}).delay()

    while not lemmatization.ready():
        await asyncio.sleep(1)

    lemmas_df = lemmatization.get()

    topics = signature('topics', args=(lemmas_df, ),
                       options={'queue': 'processing'}).delay()

    words = signature('words', args=(lemmas_df,),
                      options={'queue': 'processing'}).delay()

    while not words.ready():
        await asyncio.sleep(1)

    words_dict = words.get()

    while not topics.ready():
        await asyncio.sleep(1)

    topics_df, topics_distribution = topics.get()

    while not sentiment.ready():
        await asyncio.sleep(1)

    sentiment_df, sentiment_distribution = sentiment.get()

    while not emb_calc.ready():
        await asyncio.sleep(1)

    emb_res = emb_calc.get()

    graph = signature('graph', options={'queue': 'processing'}).delay(emb_res)

    clustering = signature('clustering', args=(emb_res, ),
                           options={'queue': 'processing'}).delay()

    while not clustering.ready() and not graph.ready():
        await asyncio.sleep(1)

    clustering_res = clustering.get()
    graph_res = graph.get()

    return clustering_res, graph_res, len(cleaned), topics_df, topics_distribution, sentiment_df, sentiment_distribution, words_dict


@app.websocket("/new")
async def analyze_new_username(websocket: WebSocket):
    await websocket.accept()

    username = await websocket.receive_text()

    username = username.lower()

    try:
        if username in [user.username.lower() for user in users + clients_users]:
            await websocket.send_json(
                get_response(STATUS_ERROR,
                             "This account is already available"))
            await websocket.close()
        else:
            await websocket.send_json(
                get_response(STATUS_OK,
                             f"Collecting tweets from {username} account"))

            await asyncio.sleep(1)

            tweets = await download_tweets(username)

            if len(tweets) == 0:
                await websocket.send_json(
                    get_response(STATUS_ERROR,
                                 f"No tweets found for {username} account")
                )
                await websocket.close()
            else:
                await websocket.send_json(
                    get_response(STATUS_OK,
                                 f"Analyzing tweets for {username}"))

                await asyncio.sleep(1)

                cluster, graph, tweets_count, topics, topics_distribution, sentiment, sentiment_distribution, words = await analyze(tweets)

                user = User(
                    username=username,
                    party=None,
                    coalition=None,
                    role=None,
                    name=None,
                    tweets_count=tweets_count,
                    x_graph2d=graph['2D_x'],
                    y_graph2d=graph['2D_y'],
                    x_graph3d=graph['3D_x'],
                    y_graph3d=graph['3D_y'],
                    z_graph3d=graph['3D_z'],
                    cluster_mean_shift_id=cluster['mean_shift_cluster'],
                    cluster_kmeans_id=cluster['kmeans_cluster'],
                    cluster_gmm_id=cluster['gmm_cluster']
                )
                clients_users.append(user)

                clients_topic_dist[username] = topics_distribution
                client_sentiment_dist[username] = sentiment_distribution
                clients_words_counts[username] = words

                full_df = tweets.merge(topics, on='id', how='right')
                full_df = full_df.merge(sentiment, on='id', how='right')
                full_df.loc[:, 'username'] = full_df['username'].apply(str.lower)
                full_df.to_sql('clients_tweets', db_engine, if_exists='append')

                await websocket.send_json(
                    get_response(STATUS_OK,
                                 f'Finished for {username}')
                )

                await websocket.close()
    except WrongUsernameException:
        await websocket.send_json(
            get_response(STATUS_ERROR,
                         f"Can't find {username} account")
        )
        await websocket.close()
    except NoTweetsLeftException:
        await websocket.send_json(
            get_response(STATUS_ERROR,
                         f"No tweets found for {username} account")
        )
        await websocket.close()
    # except Exception as e:
    #     # FIXME - this one needs fixing,
    #     #  but I don't know how to cache exception while in await state :(
    #     #  Should just catch WebSocketDisconnect
    #     # TODO - try to find a way to stop running task on disconnection
    #     print(e)
    #     print("disconnected")
