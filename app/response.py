from pydantic.main import BaseModel


class TopicDistribution(BaseModel):
    topic: int = 0
    part: float = 0.54


class WordsCounts(BaseModel):
    text: str = 'word'
    value: float = 42
