import feedparser
from datetime import datetime
import time
from typing import List, Dict, Any
import logging
from newspaper import Article as NewspaperArticle

from config.settings import RSS_SOURCES, MAX_ARTICLES_PER_SOURCE
from models.article import Article

logger = logging.getLogger(__name__)


class RSSFetcher:
    """Fetches articles from RSS feeds."""
    
    def __init__(self, sources: List[Dict[str, str]] = None):
        """
        Initialize the RSS fetcher with sources.
        
        Args:
            sources: List of dictionaries with 'name' and 'url' keys.
                     If None, uses the default sources from settings.
        """
        self.sources = sources or RSS_SOURCES
    
    def fetch_articles(self) -> List[Article]:
        """
        Fetch articles from all configured RSS sources.
        
        Returns:
            List of Article objects.
        """
        all_articles = []
        
        for source in self.sources:
            try:
                source_articles = self._fetch_from_source(source)
                all_articles.extend(source_articles)
                logger.info(f"Fetched {len(source_articles)} articles from {source['name']}")
                # Avoid hitting rate limits
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error fetching from {source['name']}: {e}")
        
        return all_articles
    
    def _fetch_from_source(self, source: Dict[str, str]) -> List[Article]:
        """
        Fetch articles from a single RSS source.
        
        Args:
            source: Dictionary with 'name' and 'url' keys.
            
        Returns:
            List of Article objects.
        """
        articles = []
        feed = feedparser.parse(source['url'])
        
        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
            try:
                # Parse the date
                if hasattr(entry, 'published_parsed'):
                    published_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                elif hasattr(entry, 'updated_parsed'):
                    published_date = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                else:
                    published_date = datetime.now()
                
                # Extract authors
                if hasattr(entry, 'authors'):
                    authors = [author.name for author in entry.authors]
                elif hasattr(entry, 'author'):
                    authors = [entry.author]
                else:
                    authors = []
                
                # Get full content using newspaper3k
                full_content = self._extract_full_content(entry.link)
                
                article = Article(
                    title=entry.title,
                    url=entry.link,
                    source_name=source['name'],
                    published_date=published_date,
                    authors=authors,
                    content=full_content
                )
                articles.append(article)
            except Exception as e:
                logger.error(f"Error processing entry from {source['name']}: {e}")
        
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