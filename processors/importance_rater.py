import logging
from typing import List, Optional
import json
import openai

from config.settings import OPENAI_API_KEY
from models.article import Article

logger = logging.getLogger(__name__)


class ImportanceRater:
    """Rates the importance of tech news articles using OpenAI."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize the importance rater.
        
        Args:
            api_key: OpenAI API key. If None, uses the key from settings.
            model: OpenAI model to use.
        """
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def rate_articles(self, articles: List[Article]) -> List[Article]:
        """
        Rate the importance of a list of articles.
        
        Args:
            articles: List of Article objects.
            
        Returns:
            The same list of Article objects with importance scores added.
        """
        for article in articles:
            try:
                article.importance_score = self._rate_article(article)
                logger.info(f"Rated article '{article.title}' with score {article.importance_score}")
            except Exception as e:
                logger.error(f"Error rating article {article.title}: {e}")
                article.importance_score = 0.0
        
        return articles
    
    def _rate_article(self, article: Article) -> float:
        """
        Rate the importance of a single article using OpenAI.
        
        Args:
            article: Article object.
            
        Returns:
            Importance score between 0.0 and 1.0.
        """
        # Create a prompt for the LLM
        prompt = f"""Rate the importance of this tech news article on a scale from 0.0 to 1.0.
Consider the following factors:
1. Technical significance and innovation
2. Industry impact and potential disruption
3. Relevance to software engineers, data scientists, and tech professionals
4. Long-term implications for the tech industry

Title: {article.title}
Summary: {article.summary}

Return your response as a JSON object with a single key 'score' with a float value between 0.0 and 1.0.
Example: {{"score": 0.85}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert tech analyst who evaluates the importance of tech news."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content.strip()
            data = json.loads(result)
            score = float(data.get('score', 0.5))
            
            # Ensure score is within bounds
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.error(f"OpenAI API error in rating: {e}")
            return 0.5  # Default middle score on failure 