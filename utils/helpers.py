from typing import List, Dict, Any
import hashlib
from datetime import datetime, timedelta
import re
import unicodedata
from urllib.parse import urlparse
import os
import logging

from models.article import Article
from config.settings import RECENT_ARTICLES_DAYS


# Add config masking functions
def mask_sensitive_value(value: str) -> str:
    """
    Mask a sensitive value, showing only first and last characters.
    
    Args:
        value: The sensitive string to mask.
        
    Returns:
        Masked string (e.g., "a***z" for "abcdefgz").
    """
    if not value or len(value) <= 4:
        return "****"
    
    return value[0] + "*" * (len(value) - 2) + value[-1]


def get_masked_config() -> Dict[str, Any]:
    """
    Get a dictionary of environment variables with sensitive values masked.
    
    Returns:
        Dictionary of masked configuration values.
    """
    sensitive_keys = [
        "OPENAI_API_KEY",
        "NEWS_API_KEY",
        "EMAIL_PASSWORD",
    ]
    
    masked_config = {}
    
    for key, value in os.environ.items():
        if key in sensitive_keys:
            masked_config[key] = mask_sensitive_value(value)
        else:
            masked_config[key] = value
    
    return masked_config


def deduplicate_articles(articles: List[Article]) -> List[Article]:
    """
    Remove duplicate articles based on content similarity.
    
    Args:
        articles: List of Article objects.
        
    Returns:
        Deduplicated list of Article objects.
    """
    seen_titles = set()
    unique_articles = []
    
    for article in articles:
        # Normalize title for comparison
        normalized_title = normalize_text(article.title.lower())
        
        # Check if we've seen a similar title
        if not any(similar_text(normalized_title, seen) for seen in seen_titles):
            seen_titles.add(normalized_title)
            unique_articles.append(article)
    
    return unique_articles


def normalize_text(text: str) -> str:
    """
    Normalize text by removing special characters, extra spaces, etc.
    
    Args:
        text: Input text.
        
    Returns:
        Normalized text.
    """
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    
    # Remove special characters and extra whitespace
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def similar_text(text1: str, text2: str, threshold: float = 0.8) -> bool:
    """
    Check if two texts are similar.
    
    Args:
        text1: First text.
        text2: Second text.
        threshold: Similarity threshold (0.0 to 1.0).
        
    Returns:
        True if the texts are similar, False otherwise.
    """
    # Simple Jaccard similarity on word sets
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return False
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    similarity = len(intersection) / len(union)
    return similarity >= threshold


def get_domain(url: str) -> str:
    """
    Extract the domain from a URL.
    
    Args:
        url: URL string.
        
    Returns:
        Domain string.
    """
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # Remove www prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]
    
    return domain


def filter_recent_articles(articles: List[Article], days: int = None) -> List[Article]:
    """
    Filter articles to only include those published within the specified number of days.
    
    Args:
        articles: List of Article objects to filter.
        days: Number of days to consider (defaults to RECENT_ARTICLES_DAYS from settings).
        
    Returns:
        List of recent Article objects.
    """
    # Use setting as default if not specified
    if days is None:
        days = RECENT_ARTICLES_DAYS
    
    # Use timezone-naive datetime for comparison to avoid timezone issues
    # Some articles might have timezone-aware dates, others might have naive dates
    now = datetime.now()
    cutoff_date = now - timedelta(days=days)
    
    recent_articles = []
    for article in articles:
        if not article.published_date:
            continue
            
        # Convert timezone-aware datetime to naive for consistent comparison
        article_date = article.published_date
        if article_date.tzinfo is not None:
            # Convert to naive by replacing tzinfo
            article_date = article_date.replace(tzinfo=None)
            
        if article_date >= cutoff_date:
            recent_articles.append(article)
            
    return recent_articles


def filter_jvm_articles(articles: List[Article]) -> List[Article]:
    """
    Filter articles related to JVM languages and frameworks.
    
    Args:
        articles: List of Article objects.
        
    Returns:
        Filtered list of JVM-related Article objects.
    """
    # Primary JVM technology keywords (core technologies)
    primary_jvm_keywords = [
        'java', 'jdk', 'jvm', 'spring', 'kotlin', 'scala', 'openjdk', 
        'jakarta ee', 'java ee', 'spring boot', 'hibernate', 'quarkus', 
        'micronaut', 'graalvm', 'jetbrains', 'intellij', 'jboss', 'tomcat', 
        'maven', 'gradle', 'javafx', 'eclipse'
    ]
    
    # Secondary JVM technology keywords (related concepts & tools)
    secondary_jvm_keywords = [
        'microservices', 'reactive', 'rest api', 'graphql', 'jpa', 'jdbc', 
        'orm', 'dependency injection', 'bytecode', 'jit compiler', 'garbage collection',
        'java virtual machine', 'jni', 'jms', 'cloud native', 'serverless', 
        'containers', 'kubernetes', 'docker', 'ci/cd', 'devops', 'jenkins',
        'apache', 'wildfly', 'weblogic', 'websphere', 'netty', 'vert.x', 'helidon',
        'spring cloud', 'spring security', 'spring data', 'jakarta', 'jee', 'j2ee', 
        'jpa', 'hibernate', 'jaxrs', 'jaxb', 'junit', 'mockito', 'testng'
    ]
    
    # Excluded topics (too generic or irrelevant)
    excluded_keywords = [
        'amazon sale', 'amazon prime', 'best deals', 'spring sale', 'spring shopping',
        'movie', 'tv show', 'subscription', 'discount', 'coupon', 'elon musk',
        'shopping', 'prime day', 'best buy', 'apple tv', 'netflix', 'ps5', 'xbox',
        'iphone', 'android phone', 'deal', 'wired', 'best gadgets'
    ]
    
    filtered_articles = []
    
    for article in articles:
        title_content = (article.title + ' ' + article.content).lower()
        
        # Count primary keywords
        primary_matches = sum(1 for keyword in primary_jvm_keywords if keyword in title_content)
        
        # Count secondary keywords
        secondary_matches = sum(1 for keyword in secondary_jvm_keywords if keyword in title_content)
        
        # Check for excluded keywords
        exclusion_matches = sum(1 for keyword in excluded_keywords if keyword in title_content)
        
        # Only include if:
        # 1. Has at least one primary keyword, OR
        # 2. Has at least three secondary keywords, AND
        # 3. Has fewer than 2 exclusion terms
        if ((primary_matches >= 1 or secondary_matches >= 3) and exclusion_matches < 2):
            filtered_articles.append(article)
    
    return filtered_articles 