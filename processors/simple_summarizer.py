import logging
import re
from typing import List, Dict, Set
from models.article import Article

logger = logging.getLogger(__name__)

class SimpleSummarizer:
    """Summarizes articles using a simple, non-ML approach."""
    
    def __init__(self, sentences_count: int = 3):
        """
        Initialize the simple summarizer.
        
        Args:
            sentences_count: Number of sentences to include in summary.
        """
        self.sentences_count = sentences_count
    
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
        Summarize an article using a simple extractive approach.
        
        Args:
            article: Article object.
            
        Returns:
            Summarized article text.
        """
        try:
            # Use content if available, otherwise use description
            text = article.content or article.description or ""
            
            if not text or len(text.strip()) < 50:
                # If we don't have enough content, use title as fallback
                return f"{article.title} - From {article.source_name}"
            
            # If text is already short enough, return it directly
            if len(text) <= 250:
                return text
            
            # If we have longer content, do a proper summarization
            if len(text) > 1000:
                # Clean the text
                cleaned_text = self._clean_text(text)
                
                # Split into sentences
                sentences = self._split_into_sentences(cleaned_text)
                
                if not sentences:
                    # If no sentences were found, use the first 250 characters
                    return text[:250] + "..."
                
                # Select important sentences
                important_sentences = self._select_important_sentences(sentences, article.title)
                
                # Create summary
                summary = " ".join(important_sentences)
            else:
                # For shorter content, use first few sentences
                cleaned_text = self._clean_text(text)
                sentences = self._split_into_sentences(cleaned_text)
                
                if not sentences:
                    # If no sentences were found, use the first 250 characters
                    return text[:250] + "..."
                    
                summary = " ".join(sentences[:3])
            
            # Limit length if needed
            if len(summary) > 250:
                summary = summary[:247] + "..."
            
            # Final check for empty summary
            if not summary or len(summary.strip()) < 20:
                return f"{article.title} - From {article.source_name}"
                
            return summary
        except Exception as e:
            logger.error(f"Error in simple summarization: {e}")
            return f"{article.title} - From {article.source_name}"
    
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
        
        return text
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using simple rules.
        
        Args:
            text: Text to split.
            
        Returns:
            List of sentences.
        """
        # Simple sentence splitting using regex
        pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
        sentences = re.split(pattern, text)
        
        # Filter out very short sentences and clean up
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        return sentences
    
    def _select_important_sentences(self, sentences: List[str], title: str) -> List[str]:
        """
        Select the most important sentences based on simple heuristics.
        
        Args:
            sentences: List of sentences.
            title: Article title for relevance calculation.
            
        Returns:
            List of important sentences.
        """
        # Use first few sentences as they often contain the main points
        if len(sentences) <= self.sentences_count:
            return sentences
        
        # Extract first and last sentences (often important)
        selected_sentences = [sentences[0]]
        
        # Get title words for relevance scoring
        title_words = set(self._get_words(title.lower()))
        
        # Score remaining sentences
        scored_sentences = []
        for i, sentence in enumerate(sentences[1:-1], 1):
            # Skip very short sentences
            if len(sentence) < 30:
                continue
                
            # Calculate relevance score
            sentence_words = set(self._get_words(sentence.lower()))
            relevance_to_title = len(title_words.intersection(sentence_words)) / max(1, len(title_words))
            
            # Score based on position and relevance
            position_score = 1.0 / (i + 1)  # Earlier is better
            
            total_score = (0.5 * relevance_to_title) + (0.5 * position_score)
            scored_sentences.append((total_score, sentence))
        
        # Sort by score and select the top N-2 sentences
        scored_sentences.sort(reverse=True)
        selected_sentences.extend([s for _, s in scored_sentences[:self.sentences_count - 2]])
        
        # Add the last sentence if available
        if len(sentences) > 2:
            selected_sentences.append(sentences[-1])
        
        return selected_sentences[:self.sentences_count]
    
    def _get_words(self, text: str) -> List[str]:
        """
        Extract meaningful words from text.
        
        Args:
            text: Text to process.
            
        Returns:
            List of words.
        """
        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into words and filter out short words
        words = [word for word in text.split() if len(word) > 3]
        
        return words
    
    def rate_importance(self, article: Article) -> float:
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


class SimpleArticleProcessor:
    """Processes articles using simple methods for summarization and importance rating."""
    
    def __init__(self, sentences_count: int = 3):
        """
        Initialize the article processor.
        
        Args:
            sentences_count: Number of sentences to include in summary.
        """
        self.summarizer = SimpleSummarizer(sentences_count)
    
    def process_articles(self, articles: List[Article]) -> List[Article]:
        """
        Process articles with simple summarization and importance rating.
        
        Args:
            articles: List of Article objects.
            
        Returns:
            Processed list of Article objects.
        """
        # Generate summaries
        summarized_articles = self.summarizer.summarize_articles(articles)
        
        # Rate importance
        for article in summarized_articles:
            article.importance_score = self.summarizer.rate_importance(article)
            logger.info(f"Rated article '{article.title}' with score {article.importance_score}")
        
        return summarized_articles 