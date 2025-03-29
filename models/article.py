from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional


class Article(BaseModel):
    """
    Model representing a tech news article with metadata, content, and AI-generated insights.
    """
    title: str
    url: str
    source_name: str
    published_date: datetime
    authors: List[str] = Field(default_factory=list)
    content: str = ""
    summary: str = ""
    importance_score: Optional[float] = None
    categories: List[str] = Field(default_factory=list)
    
    def is_recent(self, days: int = 2) -> bool:
        """Check if the article was published within the specified number of days."""
        delta = datetime.now() - self.published_date
        return delta.days <= days
    
    def __str__(self) -> str:
        return f"{self.title} ({self.source_name})" 