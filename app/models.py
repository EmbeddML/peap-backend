from dataclasses import dataclass
from typing import Optional


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
