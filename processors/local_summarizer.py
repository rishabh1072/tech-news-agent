import logging
import re
import nltk
from typing import List
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

from models.article import Article

# Download NLTK data if not already available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

logger = logging.getLogger(__name__)

class LocalSummarizer:
    """Summarizes articles using extractive summarization with sumy."""
    
    def __init__(self, language: str = 'english', sentences_count: int = 3):
        """
        Initialize the local summarizer.
        
        Args:
            language: Language of the text to summarize.
            sentences_count: Number of sentences to include in summary.
        """
        self.language = language
        self.sentences_count = sentences_count
        self.stemmer = Stemmer(language)
        self.summarizer = LsaSummarizer(self.stemmer)
        self.summarizer.stop_words = get_stop_words(language)
    
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
                article.summary = f"{article.title} - From {article.source_name}"
        
        return articles
    
    def _generate_summary(self, article: Article) -> str:
        """
        Generate a summary for a single article using extractive summarization.
        
        Args:
            article: Article object.
            
        Returns:
            Summary string.
        """
        # Ensure we have content to summarize
        if not article.content or len(article.content) < 100:
            return f"{article.title} - No content available for summarization."
        
        try:
            # Clean content
            content = self._clean_text(article.content)
            
            # Create parser
            parser = PlaintextParser.from_string(content, Tokenizer(self.language))
            
            # Get summary sentences
            summary_sentences = self.summarizer(parser.document, self.sentences_count)
            summary = " ".join(str(sentence) for sentence in summary_sentences)
            
            # Limit length if needed
            if len(summary) > 250:
                summary = summary[:247] + "..."
            
            return summary
        except Exception as e:
            logger.error(f"Error in extractive summarization: {e}")
            return f"Failed to generate summary for '{article.title}'."
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text for better summarization.
        
        Args:
            text: Text to clean.
            
        Returns:
            Cleaned text.
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove special characters that might interfere with summarization
        text = re.sub(r'[^\w\s.,!?:;()\[\]{}"\'-]', '', text)
        
        return text
    
    def _rate_importance(self, article: Article) -> float:
        """
        Rate the importance of an article based on its content and metadata.
        
        Args:
            article: Article object.
            
        Returns:
            Importance score between 0.0 and 1.0.
        """
        score = 0.5  # Lower base score (0.5 instead of 0.6)
        
        title_content = (article.title + ' ' + article.content).lower()
        
        # Technical depth indicators (give higher scores to more technical content)
        technical_indicators = [
            'tutorial', 'guide', 'how to', 'implementation', 'deploy', 'architecture',
            'benchmark', 'performance', 'optimization', 'deep dive', 'code example',
            'pattern', 'best practice', 'lesson learned', 'case study', 'analysis',
            'research', 'framework', 'library', 'algorithm', 'data structure',
            'authentication', 'authorization', 'security', 'encryption', 'api',
            'microservice', 'serverless', 'cloud native', 'container', 'kubernetes',
            'docker', 'ci/cd', 'devops', 'continuous integration', 'continuous deployment'
        ]
        
        # Critical JVM topics that deserve higher rating
        high_value_topics = [
            'java', 'spring', 'jvm', 'jdk', 'openjdk', 'spring boot', 'kotlin', 'scala',
            'jakarta ee', 'java ee', 'hibernate', 'quarkus', 'micronaut', 'graalvm', 
            'security vulnerability', 'cve', 'critical bug', 'major release', 'spring security',
            'java 17', 'java 21', 'loom', 'project loom', 'virtual threads', 'valhalla',
            'project valhalla', 'pattern matching', 'sealed classes', 'records',
            'memory leak', 'performance bottleneck', 'garbage collection', 'profiling',
            'bytecode', 'jit', 'compilation', 'classloading', 'jni', 'native interface'
        ]
        
        # JVM-specific news sources deserve a base boost
        jvm_specific_sources = [
            'infoq java', 'java code geeks', 'baeldung', 'spring blog', 'inside java',
            'eclipse blog', 'jooq blog', 'vlad mihalcea', 'dzone java', 'jetbrains blog'
        ]
        
        # Check technical depth
        technical_count = sum(1 for indicator in technical_indicators if indicator in title_content)
        technical_score = min(0.2, technical_count * 0.02)  # Up to 0.2 points for technical depth
        score += technical_score
        
        # Check for high-value topics
        high_value_count = sum(1 for topic in high_value_topics if topic in title_content)
        high_value_score = min(0.4, high_value_count * 0.04)  # Up to 0.4 points for high-value topics
        score += high_value_score
        
        # Check source - boost for JVM-specific sources
        source_name = article.source_name.lower()
        if any(jvm_source in source_name for jvm_source in jvm_specific_sources):
            score += 0.1  # Automatic 0.1 point boost for JVM-specific sources
        
        # Title analysis - does it contain high-value keywords in the title?
        title = article.title.lower()
        if any(topic in title for topic in high_value_topics):
            score += 0.1  # Extra 0.1 for high-value topic in title
        
        # Super-boost for critical JVM content
        super_boost_terms = ['critical vulnerability', 'major release', 'java lts', 'spring boot 3',
                             'spring framework 6', 'jakarta ee 10', 'java 21', 'jdk 22', 
                             'virtual threads', 'garbage collection improvement']
        
        if any(term in title_content for term in super_boost_terms):
            score += 0.2  # Major boost for critical JVM content
        
        # Penalize generic, non-JVM specific content
        generic_terms = ['best deals', 'sale', 'discount', 'movie', 'show', 'top 10',
                         'best of', 'review', 'unboxing', 'gaming', 'games']
        
        generic_count = sum(1 for term in generic_terms if term in title_content)
        if generic_count >= 2:
            score -= 0.2  # Significant penalty for generic content
        
        # Ensure score is within bounds
        return max(0.0, min(1.0, score))


class LocalArticleProcessor:
    """Processes articles using local methods for summarization and importance rating."""
    
    def __init__(self, language: str = 'english', sentences_count: int = 3):
        """
        Initialize the article processor.
        
        Args:
            language: Language of the text to summarize.
            sentences_count: Number of sentences to include in summary.
        """
        self.summarizer = LocalSummarizer(language, sentences_count)
    
    def process_articles(self, articles: List[Article]) -> List[Article]:
        """
        Process articles with local summarization and importance rating.
        
        Args:
            articles: List of Article objects.
            
        Returns:
            Processed list of Article objects.
        """
        # Generate summaries
        summarized_articles = self.summarizer.summarize_articles(articles)
        
        # Rate importance
        for article in summarized_articles:
            article.importance_score = self.summarizer._rate_importance(article)
            logger.info(f"Rated article '{article.title}' with score {article.importance_score}")
        
        return summarized_articles 