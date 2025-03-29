#!/usr/bin/env python3
import argparse
import time
import logging
import schedule
import os
from datetime import datetime
from typing import List

# Manual environment variable setting (uncomment and fill these if .env is not working)
"""
os.environ["OPENAI_API_KEY"] = "your-openai-api-key-here"
os.environ["NEWS_API_KEY"] = "your-news-api-key-here"
os.environ["EMAIL_HOST"] = "smtp.mail.yahoo.com"
os.environ["EMAIL_PORT"] = "587"
os.environ["EMAIL_USERNAME"] = "your-email@example.com"
os.environ["EMAIL_PASSWORD"] = "your-email-password"
os.environ["EMAIL_RECIPIENTS"] = "recipient1@example.com,recipient2@example.com"
"""

from config.settings import SCHEDULE_INTERVAL_HOURS, MIN_IMPORTANCE_SCORE, TOP_ARTICLES_IN_DIGEST, ENABLE_WEB_CRAWLING
from sources.rss_fetcher import RSSFetcher
from sources.news_api import NewsAPIFetcher
from sources.web_crawler import WebCrawler, enhance_articles_with_crawler
from processors.summarizer import ArticleSummarizer
from processors.importance_rater import ImportanceRater
from processors.local_summarizer import LocalArticleProcessor
from processors.simple_summarizer import SimpleArticleProcessor
from processors.adaptive_processor import AdaptiveArticleProcessor
from delivery.email_sender import EmailSender
from models.article import Article
from utils.logger import setup_logger
from utils.helpers import deduplicate_articles, filter_recent_articles, filter_jvm_articles, get_masked_config


def setup_arg_parser() -> argparse.ArgumentParser:
    """Set up and return command line argument parser."""
    parser = argparse.ArgumentParser(description="Tech News Agent - An AI-powered tech news aggregator")
    
    # General options
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--show-config", action="store_true", help="Display masked configuration and exit")
    
    # Run options
    parser.add_argument("--run-once", action="store_true", help="Run once and exit (don't schedule)")
    parser.add_argument("--no-email", action="store_true", help="Don't send email digest")
    
    # Ollama options (other processor options kept for backward compatibility but will be ignored)
    parser.add_argument("--ollama-model", type=str, default="deepseek-r1:7b", help="Specify Ollama model name (default: deepseek-r1:7b)")
    
    # Legacy options (kept for backward compatibility but will be ignored)
    parser.add_argument("--no-openai", action="store_true", help="[IGNORED] Skip OpenAI processing")
    parser.add_argument("--use-local", action="store_true", help="[IGNORED] Use local summarization")
    parser.add_argument("--use-simple", action="store_true", help="[IGNORED] Use simple summarization")
    parser.add_argument("--use-adaptive", action="store_true", help="[IGNORED] Use adaptive processor")
    parser.add_argument("--use-ollama", action="store_true", help="[IGNORED] Always using Ollama")
    parser.add_argument("--no-ollama", action="store_true", help="[IGNORED] Always using Ollama")
    
    return parser


def collect_articles() -> List[Article]:
    """Collect articles from various sources."""
    logger = logging.getLogger('tech_news_agent')
    all_articles = []
    
    # Testing mode - collect minimal articles
    testing_mode = True
    
    # Collect from RSS feeds
    try:
        rss_fetcher = RSSFetcher()
        rss_articles = rss_fetcher.fetch_articles()
        # For testing, limit to 1 article
        if testing_mode:
            rss_articles = rss_articles[:1]
        logger.info(f"Collected {len(rss_articles)} articles from RSS feeds")
        all_articles.extend(rss_articles)
    except Exception as e:
        logger.error(f"Error collecting articles from RSS feeds: {e}")
    
    # When testing, skip News API to speed things up
    if not testing_mode:
        # Collect from News API
        try:
            news_api_fetcher = NewsAPIFetcher()
            news_api_articles = news_api_fetcher.fetch_articles()
            logger.info(f"Collected {len(news_api_articles)} articles from News API")
            all_articles.extend(news_api_articles)
        except Exception as e:
            logger.error(f"Error collecting articles from News API: {e}")
    
    # Deduplicate articles
    unique_articles = deduplicate_articles(all_articles)
    # Filter for recent articles
    filtered_articles = filter_recent_articles(unique_articles)
    # Filter for JVM-related articles
    jvm_articles = filter_jvm_articles(filtered_articles)
    
    # For testing, just take first article even if not JVM-related
    if testing_mode and not jvm_articles and filtered_articles:
        logger.info("No JVM articles found, using first article for testing")
        jvm_articles = filtered_articles[:1]
    
    logger.info(f"After deduplication and filtering: {len(filtered_articles)} articles")
    logger.info(f"JVM-related articles: {len(jvm_articles)} articles")
    
    # Enhance articles with web crawling if enabled
    if ENABLE_WEB_CRAWLING:
        # For testing, limit to 1 article
        if testing_mode:
            articles_to_enhance = jvm_articles[:1]
            logger.info(f"Testing mode: enhancing only 1 article with web crawler")
        else:
            articles_to_enhance = jvm_articles
            
        enhanced_articles = enhance_articles_with_crawler(articles_to_enhance)
        return enhanced_articles
    
    return jvm_articles


def process_articles(articles: List[Article], use_local: bool = False, use_simple: bool = False, use_adaptive: bool = False, use_ollama: bool = False, ollama_model: str = "llama3", no_ollama: bool = False) -> List[Article]:
    """
    Process articles with summarization and importance rating.
    
    Args:
        articles: List of Article objects.
        use_local: Whether to use local summarization instead of OpenAI.
        use_simple: Whether to use simple summarization with no dependencies.
        use_adaptive: Whether to use adaptive processor that tries Ollama first, then falls back.
        use_ollama: Whether to use Ollama for local LLM processing.
        ollama_model: Name of the Ollama model to use if use_ollama is True.
        no_ollama: Whether to disable Ollama in the adaptive processor.
        
    Returns:
        Processed list of Article objects.
    """
    logger = logging.getLogger('tech_news_agent')
    
    if use_adaptive:
        try:
            # Default to using Ollama in adaptive processor unless no_ollama is set
            use_ollama_in_adaptive = not no_ollama
            logger.info(f"Using adaptive processor (prioritizing {'Ollama' if use_ollama_in_adaptive else 'OpenAI'})")
            adaptive_processor = AdaptiveArticleProcessor(use_ollama=use_ollama_in_adaptive, ollama_model=ollama_model)
            processed_articles = adaptive_processor.process_articles(articles)
            logger.info(f"Processed {len(processed_articles)} articles with adaptive processor")
            return processed_articles
        except Exception as e:
            logger.error(f"Error using adaptive processor: {e}")
            # Fall back to simple processor if adaptive fails
            logger.info("Falling back to simple processor")
            simple_processor = SimpleArticleProcessor()
            processed_articles = simple_processor.process_articles(articles)
            logger.info(f"Processed {len(processed_articles)} articles with simple processor")
            return processed_articles
    
    if use_ollama:
        try:
            from processors.ollama_processor import OllamaArticleProcessor
            logger.info(f"Using Ollama with model {ollama_model}")
            ollama_processor = OllamaArticleProcessor(model_name=ollama_model)
            processed_articles = ollama_processor.process_articles(articles)
            logger.info(f"Processed {len(processed_articles)} articles with Ollama")
            return processed_articles
        except Exception as e:
            logger.error(f"Error processing articles with Ollama: {e}")
            # Fall back to simple processor
            logger.info("Falling back to simple processor")
            simple_processor = SimpleArticleProcessor()
            processed_articles = simple_processor.process_articles(articles)
            return processed_articles
    
    if use_simple:
        try:
            logger.info("Using simple summarization (no dependencies)")
            simple_processor = SimpleArticleProcessor()
            processed_articles = simple_processor.process_articles(articles)
            logger.info(f"Processed {len(processed_articles)} articles with simple processor")
            return processed_articles
        except Exception as e:
            logger.error(f"Error processing articles with simple processor: {e}")
            return articles
    
    if use_local:
        try:
            logger.info("Using local summarization")
            local_processor = LocalArticleProcessor()
            processed_articles = local_processor.process_articles(articles)
            logger.info(f"Processed {len(processed_articles)} articles with local processor")
            return processed_articles
        except Exception as e:
            logger.error(f"Error processing articles with local processor: {e}")
            return articles
    
    # Use OpenAI
    try:
        # Summarize
        logger.info("Summarizing articles with OpenAI")
        summarizer = ArticleSummarizer()
        summarized_articles = summarizer.summarize_articles(articles)
        logger.info(f"Summarized {len(summarized_articles)} articles")
        
        # Rate importance
        logger.info("Rating article importance with OpenAI")
        importance_rater = ImportanceRater()
        rated_articles = importance_rater.rate_articles(summarized_articles)
        logger.info(f"Rated {len(rated_articles)} articles")
        
        return rated_articles
    except Exception as e:
        logger.error(f"Error processing articles with OpenAI: {e}")
        return articles


def deliver_digest(articles: List[Article], send_email: bool = True) -> None:
    """Deliver tech news digest via email and display on console."""
    logger = logging.getLogger('tech_news_agent')
    
    logger.info(f"Starting digest delivery with {len(articles)} articles")
    
    # Debug article scores
    scores_info = [f"{a.title[:30]}... : {a.importance_score}" for a in articles[:10]]
    logger.info(f"Sample article scores: {scores_info}")
    
    # Filter by minimum importance score if available
    if any(a.importance_score is not None for a in articles):
        important_articles = [a for a in articles if a.importance_score and a.importance_score >= MIN_IMPORTANCE_SCORE]
        logger.info(f"After importance filter: {len(important_articles)} articles remain (min score: {MIN_IMPORTANCE_SCORE})")
    else:
        # If no importance scores, take all articles
        important_articles = articles
        logger.info(f"No importance scores found, keeping all {len(important_articles)} articles")
    
    # Limit articles count if needed
    if len(important_articles) > TOP_ARTICLES_IN_DIGEST * 2:
        important_articles = important_articles[:TOP_ARTICLES_IN_DIGEST * 2]
        logger.info(f"Limited to top {len(important_articles)} articles")
    
    # Sort by importance score if available, otherwise by date
    if any(a.importance_score is not None for a in important_articles):
        sorted_articles = sorted(important_articles, key=lambda x: x.importance_score or 0, reverse=True)
        logger.info("Articles sorted by importance score")
    else:
        sorted_articles = sorted(important_articles, key=lambda x: x.published_date, reverse=True)
        logger.info("Articles sorted by published date")
    
    # Take top N articles
    top_articles = sorted_articles[:TOP_ARTICLES_IN_DIGEST]
    logger.info(f"Selected top {len(top_articles)} articles for digest")
    
    if not top_articles:
        logger.warning("No articles to deliver")
        return
    
    # Print to console
    print("\n" + "=" * 80)
    print(f"TECH NEWS DIGEST - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    for i, article in enumerate(top_articles):
        importance = article.importance_score if article.importance_score is not None else "N/A"
        importance_str = f"{importance:.2f}" if isinstance(importance, float) else importance
        
        print(f"\n{i+1}. {article.title}")
        print(f"   Source: {article.source_name} | Importance: {importance_str}")
        print(f"   URL: {article.url}")
        print(f"   Summary: {article.summary}")
    
    print("\n" + "=" * 80 + "\n")
    
    # Send email if enabled
    if send_email:
        try:
            email_sender = EmailSender()
            success = email_sender.send_digest(top_articles)
            if success:
                logger.info("Email digest sent successfully")
            else:
                logger.error("Failed to send email digest")
        except Exception as e:
            logger.error(f"Error sending email digest: {e}")


def display_masked_config() -> None:
    """Display masked configuration values."""
    print("\n" + "=" * 80)
    print("MASKED CONFIGURATION")
    print("=" * 80)
    
    masked_config = get_masked_config()
    
    # Display relevant config values
    relevant_keys = [
        "OPENAI_API_KEY", 
        "NEWS_API_KEY",
        "EMAIL_HOST",
        "EMAIL_PORT",
        "EMAIL_USERNAME",
        "EMAIL_PASSWORD",
        "EMAIL_RECIPIENTS",
        "SCHEDULE_INTERVAL_HOURS",
        "TOP_ARTICLES_IN_DIGEST",
        "MIN_IMPORTANCE_SCORE"
    ]
    
    for key in relevant_keys:
        if key in masked_config:
            print(f"{key}: {masked_config[key]}")
    
    print("=" * 80 + "\n")


def job(skip_openai: bool = False, use_local: bool = False, use_simple: bool = False, use_adaptive: bool = False, use_ollama: bool = True, ollama_model: str = "deepseek-r1:7b", no_ollama: bool = False) -> None:
    """
    Main job function that runs the tech news agent workflow.
    
    Args:
        skip_openai: Whether to skip OpenAI processing (summarization and rating).
        use_local: Whether to use local summarization instead of OpenAI.
        use_simple: Whether to use simple summarization with no dependencies.
        use_adaptive: Whether to use adaptive processor that tries Ollama first, then falls back.
        use_ollama: Whether to use Ollama for local LLM processing.
        ollama_model: Name of the Ollama model to use if use_ollama is True.
        no_ollama: Whether to disable Ollama in the adaptive processor.
    """
    logger = logging.getLogger('tech_news_agent')
    logger.info("Starting tech news agent job")
    
    start_time = time.time()
    
    try:
        # Collect articles
        articles = collect_articles()
        
        if not articles:
            logger.warning("No articles collected")
            return
        
        # Limit to only 1 article for faster processing
        articles = articles[:1]
        logger.info(f"Limited to 1 article for faster processing")
        
        # Process articles - ONLY using simple processor for testing (faster)
        logger.info(f"Using simple processor for speed")
        simple_processor = SimpleArticleProcessor()
        processed_articles = simple_processor.process_articles(articles)
        
        # Deliver digest
        deliver_digest(processed_articles)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Tech news agent job completed in {elapsed_time:.2f} seconds")
    
    except Exception as e:
        logger.error(f"Error in tech news agent job: {e}")


def main() -> None:
    """Main entry point."""
    # Parse command line arguments
    parser = setup_arg_parser()
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logger(log_level=log_level)
    
    logger.info("Starting Tech News Agent")
    
    # Show masked configuration if requested
    if args.show_config:
        display_masked_config()
    
    # Note: other flags like use_local, use_simple, etc. will be ignored - always using Ollama
    ollama_model = args.ollama_model if args.ollama_model else "deepseek-r1:7b"
    logger.info(f"Using Ollama exclusively with model: {ollama_model}")
    
    if args.run_once:
        logger.info("Running in one-time mode")
        job(ollama_model=ollama_model)
    else:
        logger.info(f"Running in scheduled mode (every {SCHEDULE_INTERVAL_HOURS} hours)")
        
        # Run immediately
        job(ollama_model=ollama_model)
        
        # Schedule recurring job
        def scheduled_job():
            job(ollama_model=ollama_model)
        
        schedule.every(SCHEDULE_INTERVAL_HOURS).hours.do(scheduled_job)
        
        # Run the scheduler
        logger.info("Scheduler started")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down")


if __name__ == "__main__":
    main() 