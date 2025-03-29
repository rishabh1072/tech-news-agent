import logging
from typing import List, Optional
import openai
from openai import OpenAIError, RateLimitError, APIError

from models.article import Article
from processors.summarizer import ArticleSummarizer
from processors.importance_rater import ImportanceRater
from processors.local_summarizer import LocalArticleProcessor
from processors.simple_summarizer import SimpleArticleProcessor
from processors.ollama_processor import OllamaArticleProcessor

logger = logging.getLogger(__name__)

class AdaptiveArticleProcessor:
    """
    Adaptively processes articles using different methods based on availability:
    1. Ollama (if installed and available) - prioritized
    2. OpenAI (if quota available) - used as fallback
    3. Local summarization with sumy (if above methods fail)
    4. Simple summarization (as a last resort)
    """
    
    def __init__(self, use_ollama: bool = True, ollama_model: str = "llama3"):
        """Initialize the adaptive processor with all available processors."""
        self.openai_processor = None
        self.ollama_processor = None
        
        # Initialize Ollama processor if enabled (prioritized)
        if use_ollama:
            try:
                self.ollama_processor = OllamaArticleProcessor(model_name=ollama_model)
                logger.info(f"Ollama processor initialized with model: {ollama_model}")
            except Exception as e:
                logger.warning(f"Could not initialize Ollama processor: {e}")
                self.ollama_processor = None
        
        # Initialize OpenAI processor (fallback option)
        try:
            self.summarizer = ArticleSummarizer()
            self.importance_rater = ImportanceRater()
            self.openai_processor = True
            logger.info("OpenAI processor initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI processor: {e}")
            self.openai_processor = None
        
        # Initialize local processor
        try:
            self.local_processor = LocalArticleProcessor()
            logger.info("Local processor initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize local processor: {e}")
            self.local_processor = None
        
        # Initialize simple processor (always available as fallback)
        self.simple_processor = SimpleArticleProcessor()
        logger.info("Simple processor initialized successfully")
    
    def process_articles(self, articles: List[Article]) -> List[Article]:
        """
        Process articles using the best available method.
        
        Args:
            articles: List of Article objects.
            
        Returns:
            Processed list of Article objects.
        """
        if not articles:
            return []
        
        result_articles = []
        failed_articles = []
        
        # Try Ollama first if available (prioritized)
        if self.ollama_processor:
            logger.info(f"Attempting to use Ollama for {len(articles)} articles")
            try:
                ollama_processed = self.ollama_processor.process_articles(articles)
                
                # Verify importance scores
                for article in ollama_processed:
                    if article.importance_score is None or article.importance_score <= 0:
                        logger.warning(f"Ollama missing importance score: {article.title[:30]}...")
                        article.importance_score = 0.7  # Assign default score
                
                result_articles.extend(ollama_processed)
                logger.info(f"Successfully processed {len(ollama_processed)} articles with Ollama")
                failed_articles = []
                # Return immediately if all articles were processed successfully
                return result_articles
            except Exception as e:
                logger.warning(f"Ollama processing failed: {e}")
                # Keep articles for next processor
                failed_articles = articles
        else:
            # Ollama not available
            failed_articles = articles
        
        # Try OpenAI for failed articles as fallback
        if failed_articles and self.openai_processor:
            logger.info("Attempting to use OpenAI for processing articles")
            try:
                # Process with OpenAI
                summarized_articles = self._process_with_openai(failed_articles)
                result_articles.extend(summarized_articles)
                logger.info(f"Successfully processed {len(summarized_articles)} articles with OpenAI")
                failed_articles = []
            except (RateLimitError, APIError) as e:
                # OpenAI quota exceeded or API error
                logger.warning(f"OpenAI processing failed: {e}")
                # Keep failed_articles for next processor
            except Exception as e:
                logger.error(f"Unexpected error with OpenAI processing: {e}")
                # Keep failed_articles for next processor
        
        # Try local processing for failed articles
        if failed_articles and self.local_processor:
            logger.info(f"Attempting to use local processor for {len(failed_articles)} articles")
            try:
                local_processed = self.local_processor.process_articles(failed_articles)
                
                # Verify importance scores
                for article in local_processed:
                    if article.importance_score is None or article.importance_score <= 0:
                        logger.warning(f"Article missing importance score: {article.title[:30]}...")
                        article.importance_score = 0.7  # Assign default score
                
                result_articles.extend(local_processed)
                logger.info(f"Successfully processed {len(local_processed)} articles with local processor")
                failed_articles = []
            except Exception as e:
                logger.warning(f"Local processing failed: {e}")
                # Keep failed_articles for simple processor
        
        # Use simple processor as last resort
        if failed_articles:
            logger.info(f"Using simple processor for {len(failed_articles)} articles")
            try:
                simple_processed = self.simple_processor.process_articles(failed_articles)
                
                # Verify importance scores for simple processor too
                for article in simple_processed:
                    if article.importance_score is None or article.importance_score <= 0:
                        logger.warning(f"Simple processor missing importance score: {article.title[:30]}...")
                        article.importance_score = 0.7  # Assign default score
                
                result_articles.extend(simple_processed)
                logger.info(f"Processed {len(simple_processed)} articles with simple processor")
            except Exception as e:
                logger.error(f"Error in simple processing: {e}")
                # Last resort - assign basic scores to the failed articles
                for article in failed_articles:
                    article.summary = f"{article.title} - From {article.source_name}"
                    article.importance_score = 0.6
                result_articles.extend(failed_articles)
                logger.warning(f"Used very basic processing for {len(failed_articles)} articles")
        
        # Final check for missing scores
        for article in result_articles:
            if article.importance_score is None:
                article.importance_score = 0.7
        
        logger.info(f"Adaptive processor returned {len(result_articles)} articles with scores")
        return result_articles
    
    def _process_with_openai(self, articles: List[Article]) -> List[Article]:
        """
        Process articles using OpenAI.
        
        Args:
            articles: List of Article objects.
            
        Returns:
            Processed list of Article objects.
        """
        # Summarize articles
        summarized_articles = self.summarizer.summarize_articles(articles)
        
        # Rate importance
        rated_articles = self.importance_rater.rate_articles(summarized_articles)
        
        # Ensure all articles have importance scores
        for article in rated_articles:
            if article.importance_score is None:
                logger.warning(f"OpenAI processing missing importance score: {article.title[:30]}...")
                article.importance_score = 0.7  # Assign default score
        
        return rated_articles 