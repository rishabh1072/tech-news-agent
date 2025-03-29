import requests
from datetime import datetime, timedelta
import logging
from typing import List, Optional
from newspaper import Article as NewspaperArticle

from config.settings import NEWS_API_KEY, NEWS_API_SOURCES, MAX_ARTICLES_PER_SOURCE
from models.article import Article

logger = logging.getLogger(__name__)


class NewsAPIFetcher:
    """Fetches articles from News API."""
    
    BASE_URL = "https://newsapi.org/v2/everything"
    
    def __init__(self, api_key: Optional[str] = None, sources: Optional[List[str]] = None):
        """
        Initialize the News API fetcher.
        
        Args:
            api_key: News API key. If None, uses the key from settings.
            sources: List of source IDs. If None, uses the sources from settings.
        """
        self.api_key = api_key or NEWS_API_KEY
        if not self.api_key:
            raise ValueError("News API key is required")
        
        self.sources = sources or NEWS_API_SOURCES
    
    def fetch_articles(self, days_back: int = 2) -> List[Article]:
        """
        Fetch articles from News API.
        
        Args:
            days_back: Number of days to look back for articles.
            
        Returns:
            List of Article objects.
        """
        all_articles = []
        
        # Calculate date range
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        for source in self.sources:
            try:
                source_articles = self._fetch_from_source(source, from_date)
                all_articles.extend(source_articles)
                logger.info(f"Fetched {len(source_articles)} articles from NewsAPI - {source}")
            except Exception as e:
                logger.error(f"Error fetching from NewsAPI - {source}: {e}")
        
        return all_articles
    
    def _fetch_from_source(self, source: str, from_date: str) -> List[Article]:
        """
        Fetch articles from a single News API source.
        
        Args:
            source: Source ID.
            from_date: From date in YYYY-MM-DD format.
            
        Returns:
            List of Article objects.
        """
        params = {
            'sources': source,
            'from': from_date,
            'sortBy': 'publishedAt',
            'apiKey': self.api_key,
            'pageSize': MAX_ARTICLES_PER_SOURCE
        }
        
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        articles = []
        for item in data.get('articles', []):
            try:
                # Parse date
                published_date = datetime.fromisoformat(item['publishedAt'].replace('Z', '+00:00'))
                
                # Extract full content
                full_content = self._extract_full_content(item['url'])
                
                article = Article(
                    title=item['title'],
                    url=item['url'],
                    source_name=item['source']['name'],
                    published_date=published_date,
                    authors=[item['author']] if item.get('author') else [],
                    content=full_content or item.get('description', '')
                )
                articles.append(article)
            except Exception as e:
                logger.error(f"Error processing item from {source}: {e}")
        
        return articles
    
    def _extract_full_content(self, url: str) -> str:
        """
        Extract the full content of an article using newspaper3k.
        
        Args:
            url: URL of the article.
            
        Returns:
            String containing the article text.
        """
        try:
            article = NewspaperArticle(url)
            article.download()
            article.parse()
            return article.text
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return "" 