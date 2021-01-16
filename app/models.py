from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel


@dataclass
class TwitterPoint2d:
    twitter_name: str
    x: float
    y: float


@dataclass
class TwitterPoint3d(TwitterPoint2d):
    z: float


@dataclass
class TwitterUser:
    twitter_name: str
    party: Optional[str]
    coalition: Optional[str]


class User(BaseModel):
    username: str
    party: str
    coalition: str
    role: str
    name: str
    tweets_count: int
    x_graph2d: float
    y_graph2d: float
    x_graph3d: float
    y_graph3d: float
    z_graph3d: float
    cluster_dbscan_id: int
    cluster_kmeans_id: int
    cluster_pam_id: int


class Party(BaseModel):
    party_id: int
    name: str
    coalition: str


class Coalition(BaseModel):
    coalition_id: int
    name: str
