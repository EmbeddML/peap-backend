from pydantic.main import BaseModel


class TopicDistribution(BaseModel):
    topic: int = 0
    part: float = 0.54
