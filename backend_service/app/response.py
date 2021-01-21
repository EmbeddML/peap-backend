"""Classes used for API documentation purposes. Values are examples"""


from pydantic.main import BaseModel


class TopicDistribution(BaseModel):
    topic: int = 0
    part: float = 0.54


class WordsCounts(BaseModel):
    text: str = 'word'
    value: float = 42


class ProfileImage(BaseModel):
    url: str = 'url_to_pic'
