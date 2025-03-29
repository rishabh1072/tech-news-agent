import logging
from typing import List, Optional
import openai

from config.settings import OPENAI_API_KEY, SUMMARY_MAX_LENGTH
from models.article import Article

logger = logging.getLogger(__name__)


class ArticleSummarizer:
    """Summarizes articles using OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize the article summarizer.
        
        Args:
            api_key: OpenAI API key. If None, uses the key from settings.
            model: OpenAI model to use.
        """
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def summarize_articles(self, articles: List[Article]) -> List[Article]:
        """
        Generate summaries for a list of articles.
        
        Args:
            articles: List of Article objects.
            
        Returns:
            The same list of Article objects with summaries added.
        """
        for article in articles:
            try:
                article.summary = self._generate_summary(article)
                logger.info(f"Generated summary for article: {article.title}")
            except Exception as e:
                logger.error(f"Error generating summary for article {article.title}: {e}")
        
        return articles
    
    def _generate_summary(self, article: Article) -> str:
        """
        Generate a summary for a single article using OpenAI.
        
        Args:
            article: Article object.
            
        Returns:
            Summary string.
        """
        # Ensure we have content to summarize
        if not article.content:
            return "No content available to summarize."
        
        # Truncate content if it's too long (tokens are approx 4 chars per token)
        max_content_chars = 12000  # ~3000 tokens
        content = article.content[:max_content_chars]
        
        # Create a prompt for the LLM
        prompt = f"""Summarize the following tech article in one concise paragraph.
Keep the summary under {SUMMARY_MAX_LENGTH} characters.
Focus on the key technical details and why this news is important to tech professionals.

Title: {article.title}
Source: {article.source_name}
Content: {content}

Summary:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a tech journalist who writes clear, concise summaries of tech news."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3,
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return "Failed to generate summary." 