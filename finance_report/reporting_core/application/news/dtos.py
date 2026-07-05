from datetime import datetime
from ...domain.shared_values import ValueObject

class NewsItem(ValueObject):
    headline: str
    url: str
    publisher: str
    published_at: datetime
    summary: str | None = None       # provided snippet only — never scraped body
