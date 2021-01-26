from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    username: str
    party: Optional[str]
    coalition: Optional[str]
    role: Optional[str]
    name: Optional[str]
    tweets_count: int
    x_graph2d: float
    y_graph2d: float
    x_graph3d: float
    y_graph3d: float
    z_graph3d: float
    cluster_mean_shift_id: int
    cluster_kmeans_id: int
    cluster_gmm_id: int


class Party(BaseModel):
    party_id: int
    name: str
    coalition: str


class Coalition(BaseModel):
    coalition_id: int
    name: str


class Tweet(BaseModel):
    tweet_id: int
    twitter_link: str
    username: str
    tweet_text: str
    topic: int
    topic_proba: float
    sentiment: str
