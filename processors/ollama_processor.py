import logging
import requests
import json
from typing import List, Dict, Any, Optional
from models.article import Article

logger = logging.getLogger(__name__)

class OllamaProcessor:
    """
    Processes articles using locally hosted Ollama models for summarization and importance rating.
    """
    
    def __init__(
        self, 
        model_name: str = "llama3", 
        host: str = "http://localhost:11434",
        fallback_processor = None
    ):
        """
        Initialize the Ollama processor.
        
        Args:
            model_name: Name of the Ollama model to use, default is llama3
            host: Host URL for Ollama API, default is http://localhost:11434
            fallback_processor: Optional processor to use if Ollama fails
        """
        self.model_name = model_name
        self.host = host
        self.api_base = f"{host}/api"
        self.fallback_processor = fallback_processor
        
        # Check if Ollama is available
        self.available = self._check_availability()
        if self.available:
            logger.info(f"Ollama processor initialized with model: {model_name}")
        else:
            logger.warning(f"Ollama not available at {host}. Will use fallback processor if provided.")
    
    def _check_availability(self) -> bool:
        """Check if Ollama server is available and the model exists."""
        try:
            # Try to list models to check if server is running
            response = requests.get(f"{self.api_base}/tags", timeout=5)
            if response.status_code != 200:
                return False
                
            # Check if our model is available
            models = response.json().get("models", [])
            available_models = [model.get("name") for model in models]
            
            logger.info(f"Available Ollama models: {available_models}")
            
            # First check for exact match
            if self.model_name in available_models:
                return True
                
            # If exact match not found, try to find if model is available with a different tag
            base_model_name = self.model_name.split(':')[0] if ':' in self.model_name else self.model_name
            for model in available_models:
                if model.startswith(f"{base_model_name}:") or model == base_model_name:
                    logger.info(f"Model {self.model_name} not found, but found similar model: {model}")
                    # Update to use the available model
                    self.model_name = model
                    return True
                    
            # If no match found, try to use the first available model as fallback
            if available_models:
                logger.warning(f"Model {self.model_name} not found. Using {available_models[0]} instead")
                self.model_name = available_models[0]
                return True
                
            logger.warning(f"Model {self.model_name} not found in Ollama. Available models: {available_models}")
            return False
                
        except Exception as e:
            logger.error(f"Error checking Ollama availability: {e}")
            return False
    
    def process_articles(self, articles: List[Article]) -> List[Article]:
        """
        Process articles with Ollama for summarization and importance rating.
        
        Args:
            articles: List of Article objects.
            
        Returns:
            Processed list of Article objects with summaries and importance scores.
        """
        if not self.available:
            if self.fallback_processor:
                logger.info("Using fallback processor since Ollama is not available")
                return self.fallback_processor.process_articles(articles)
            else:
                logger.error("Ollama not available and no fallback processor provided")
                return articles
                
        processed_articles = []
        for article in articles:
            try:
                # Generate summary
                article.summary = self._generate_summary(article)
                
                # Rate importance
                article.importance_score = self._rate_importance(article)
                
                logger.info(f"Processed article with Ollama: {article.title[:40]}...")
                processed_articles.append(article)
            except Exception as e:
                logger.error(f"Error processing article with Ollama: {e}")
                if article.summary is None:
                    article.summary = f"{article.title} - From {article.source_name}"
                if article.importance_score is None:
                    article.importance_score = 0.5
                processed_articles.append(article)
        
        return processed_articles
    
    def _generate_summary(self, article: Article) -> str:
        """
        Generate a summary for an article using Ollama.
        
        Args:
            article: Article object.
            
        Returns:
            Summary text.
        """
        # Determine what text to summarize
        text_to_summarize = article.content or article.description or ""
        if not text_to_summarize:
            return f"{article.title} - From {article.source_name}"
            
        # Limit text to avoid overloading the model
        if len(text_to_summarize) > 10000:
            text_to_summarize = text_to_summarize[:10000] + "..."
        
        # Create prompt for summarization
        prompt = f"""Please create a concise summary of the following article.
        Focus on the key points and main takeaways in 2-3 sentences.
        Make it informative and straightforward.
        
        Title: {article.title}
        
        Article content:
        {text_to_summarize}
        
        Summary:"""
        
        try:
            # Call Ollama API for generation
            response = requests.post(
                f"{self.api_base}/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 300,
                    }
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            summary = result.get("response", "").strip()
            
            # Check if we got a valid summary
            if not summary or len(summary) < 20:
                return f"{article.title} - From {article.source_name}"
                
            # Limit length
            if len(summary) > 250:
                summary = summary[:247] + "..."
                
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary with Ollama: {e}")
            return f"{article.title} - From {article.source_name}"
    
    def _rate_importance(self, article: Article) -> float:
        """
        Rate the importance of an article using Ollama.
        
        Args:
            article: Article object.
            
        Returns:
            Importance score between 0.0 and 1.0.
        """
        # If we don't have a title or content, rate it as medium importance
        if not article.title or not (article.content or article.description):
            return 0.5
        
        # Combine title and truncated content for analysis
        text_to_analyze = article.title
        if article.content:
            # Limit content to avoid overloading the model
            truncated_content = article.content[:5000] if len(article.content) > 5000 else article.content
            text_to_analyze += "\n\n" + truncated_content
        elif article.description:
            text_to_analyze += "\n\n" + article.description
        
        # Create prompt for importance rating
        prompt = f"""Please rate the importance of this article for Java/JVM developers on a scale from 0.0 to 1.0.
        
        Consider these factors in your rating:
        1. Technical depth and relevance to JVM technologies
        2. Focus on Java, Spring, Kotlin, Scala, or other JVM languages
        3. Coverage of important releases, updates, or critical issues
        4. Practical value for JVM developers
        
        Article to evaluate:
        Title: {article.title}
        Source: {article.source_name}
        Content: {text_to_analyze}
        
        Output only a single number between 0.0 and 1.0 as your rating. Higher values (closer to 1.0) mean more important.
        Rating:"""
        
        try:
            # Call Ollama API for importance rating
            response = requests.post(
                f"{self.api_base}/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                    }
                },
                timeout=15
            )
            
            response.raise_for_status()
            result = response.json()
            rating_text = result.get("response", "").strip()
            
            # Extract numeric rating from response
            import re
            rating_match = re.search(r'(\d+\.\d+|\d+)', rating_text)
            if rating_match:
                rating = float(rating_match.group(1))
                # Ensure rating is within bounds
                rating = max(0.0, min(1.0, rating))
                return rating
            
            # Default to medium importance if no valid rating found
            return 0.5
            
        except Exception as e:
            logger.error(f"Error rating importance with Ollama: {e}")
            return 0.5


class OllamaArticleProcessor:
    """
    Article processor that uses Ollama for summarization and importance rating.
    """
    
    def __init__(
        self, 
        model_name: str = "llama3", 
        host: str = "http://localhost:11434",
        fallback_processor = None
    ):
        """
        Initialize the Ollama article processor.
        
        Args:
            model_name: Name of the Ollama model to use, default is llama3
            host: Host URL for Ollama API, default is http://localhost:11434
            fallback_processor: Optional processor to use if Ollama fails
        """
        # If no fallback specified, use SimpleArticleProcessor
        if fallback_processor is None:
            from processors.simple_summarizer import SimpleArticleProcessor
            fallback_processor = SimpleArticleProcessor()
            
        self.processor = OllamaProcessor(model_name, host, fallback_processor)
        
    def process_articles(self, articles: List[Article]) -> List[Article]:
        """
        Process articles with Ollama.
        
        Args:
            articles: List of Article objects.
            
        Returns:
            Processed list of Article objects.
        """
        processed = []
        
        # If the processor is available, process normally
        if self.processor.available:
            return self.processor.process_articles(articles)
            
        # If not available, at least make sure each article has a summary and importance score
        for article in articles:
            if not article.summary:
                article.summary = f"{article.title} - From {article.source_name}"
            if article.importance_score is None:
                article.importance_score = 0.5
            processed.append(article)
            
        return processed 