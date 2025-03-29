import logging
import requests
from bs4 import BeautifulSoup
import time
import random
from newspaper import Article
from urllib.parse import urlparse
from typing import List

logger = logging.getLogger(__name__)

class WebCrawler:
    """
    Web crawler to extract full article content from various news sources.
    Uses newspaper3k library for article extraction with fallback to custom BeautifulSoup parsing.
    """
    
    def __init__(self, respect_robots=True, user_agent=None):
        """
        Initialize web crawler.
        
        Args:
            respect_robots: Whether to respect robots.txt (recommended for production)
            user_agent: Custom user agent string to use for requests
        """
        self.respect_robots = respect_robots
        self.user_agent = user_agent or 'JVM Tech News Agent/1.0 (+https://github.com/your-repo/tech-news-agent)'
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/'
        }
        # Add some delay between requests to be respectful to servers
        self.min_delay = 1.0  # seconds
        self.max_delay = 3.0  # seconds
        
        # Some sites block bots, so we need to track failures
        self.known_bot_blockers = [
            'wsj.com',
            'nytimes.com',
            'bloomberg.com',
            'medium.com',
            'ft.com'
        ]
    
    def crawl_article(self, url):
        """
        Crawl a news article and extract its full content.
        
        Args:
            url: URL of the article to crawl
            
        Returns:
            dict with keys:
                - title: Article title
                - content: Full article content
                - publish_date: Publication date if available
                - authors: List of authors if available
                - success: Boolean indicating if crawling was successful
        """
        domain = urlparse(url).netloc
        
        # Check if site is known to block bots
        if any(blocker in domain for blocker in self.known_bot_blockers):
            logger.warning(f"Skipping crawl for {url} - domain is known to block bots")
            return {
                'title': None,
                'content': None,
                'publish_date': None,
                'authors': None,
                'success': False
            }
        
        # Add some delay to be respectful
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
        
        try:
            # Try using newspaper3k first (best for article extraction)
            article = Article(url)
            article.download()
            article.parse()
            
            # Check if content was successfully extracted
            if article.text and len(article.text) > 200:
                return {
                    'title': article.title,
                    'content': article.text,
                    'publish_date': article.publish_date,
                    'authors': article.authors,
                    'success': True
                }
            
            # If newspaper3k fails, try custom extraction with BeautifulSoup
            return self._extract_with_beautifulsoup(url)
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return {
                'title': None,
                'content': None,
                'publish_date': None,
                'authors': None,
                'success': False
            }
    
    def _extract_with_beautifulsoup(self, url):
        """
        Extract article content using BeautifulSoup as a fallback method.
        
        Args:
            url: URL to crawl
            
        Returns:
            dict with article data
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = soup.title.text.strip() if soup.title else "No title found"
            
            # Extract main content (this is a simplified approach)
            # Most articles have content in <p> tags within <article> or <main> or <div class="content">
            article_tag = soup.find('article') or soup.find('main')
            
            if not article_tag:
                # Try common content division classes
                for class_name in ['content', 'article', 'post', 'entry', 'story']:
                    article_tag = soup.find('div', class_=lambda c: c and class_name in c.lower())
                    if article_tag:
                        break
            
            # Extract paragraphs from the identified content area, or from the entire document if not found
            content_area = article_tag if article_tag else soup
            paragraphs = content_area.find_all('p')
            
            # Combine all paragraph text
            content = '\n\n'.join(p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 40)
            
            return {
                'title': title,
                'content': content,
                'publish_date': None,  # BeautifulSoup approach doesn't extract date reliably
                'authors': None,       # BeautifulSoup approach doesn't extract authors reliably
                'success': bool(content and len(content) > 200)
            }
            
        except Exception as e:
            logger.error(f"BeautifulSoup extraction failed for {url}: {e}")
            return {
                'title': None,
                'content': None,
                'publish_date': None,
                'authors': None,
                'success': False
            }
    
    def enhance_article(self, article):
        """
        Enhance an existing article object by crawling its URL to get the full content.
        
        Args:
            article: Article object with at least a url attribute
            
        Returns:
            Enhanced article object with full content
        """
        if not article.url:
            logger.warning("Cannot enhance article without URL")
            return article
        
        logger.info(f"Enhancing article: {article.title[:40]}...")
        
        # Skip if article already has substantial content
        if article.content and len(article.content) > 1000:
            logger.info(f"Article already has substantial content: {article.title[:40]}")
            return article
        
        # Crawl the article
        crawl_result = self.crawl_article(article.url)
        
        if crawl_result['success']:
            # Update article with crawled content if successful
            if not article.title and crawl_result['title']:
                article.title = crawl_result['title']
                
            # Always update content if we got it
            if crawl_result['content']:
                article.content = crawl_result['content']
                
            logger.info(f"Successfully enhanced article: {article.title[:40]}")
        else:
            logger.warning(f"Failed to enhance article: {article.title[:40]}")
        
        return article

def enhance_articles_with_crawler(articles: List[Article]) -> List[Article]:
    """
    Enhance articles with additional content fetched using the web crawler.
    
    Args:
        articles: List of Article objects to enhance.
        
    Returns:
        List of enhanced Article objects.
    """
    # For testing, only process up to 1 article
    testing_mode = True
    if testing_mode:
        articles_to_process = articles[:1]
    else:
        articles_to_process = articles
    
    crawler = WebCrawler()
    enhanced_count = 0
    
    logger.info(f"Enhancing {len(articles_to_process)} articles with web crawler")
    
    # Show progress in batches
    for i, article in enumerate(articles_to_process):
        # Log progress every 5 articles
        if i % 5 == 0:
            logger.info(f"Crawling progress: {i}/{len(articles_to_process)} articles")
            
        # Skip articles that already have good content
        if article.content and len(article.content) > 1000:
            continue
            
        try:
            # Crawl the article
            result = crawler.crawl_article(article.url)
            
            if result['success']:
                # Update article with enhanced content
                if result['content'] and len(result['content']) > len(article.content or ''):
                    article.content = result['content']
                    enhanced_count += 1
                    
                # Update other fields if available
                if result['publish_date'] and not article.published_date:
                    article.published_date = result['publish_date']
                    
                if result['authors'] and not article.authors:
                    article.authors = result['authors']
        except Exception as e:
            logger.error(f"Failed to enhance article: {article.title[:30]}...")
    
    logger.info(f"Successfully enhanced {enhanced_count} articles with web crawler")
    return articles 