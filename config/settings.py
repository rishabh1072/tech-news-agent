import os
from typing import Dict, List, Any
from dotenv import load_dotenv
import sys

# Print working directory for debugging
print(f"Current working directory: {os.getcwd()}")

# Check if .env file exists
env_path = os.path.join(os.getcwd(), '.env')
print(f".env file exists: {os.path.exists(env_path)}")

# Load environment variables
load_dotenv(dotenv_path=env_path, verbose=True)

# Print environment variables for debugging (masked)
print("Environment variables loaded:")
for key in ["OPENAI_API_KEY", "NEWS_API_KEY"]:
    value = os.getenv(key)
    masked = "Not set" if not value else f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "Set but too short"
    print(f"  {key}: {masked}")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Print API keys status
print(f"OPENAI_API_KEY loaded: {'Yes' if OPENAI_API_KEY else 'No'}")
print(f"NEWS_API_KEY loaded: {'Yes' if NEWS_API_KEY else 'No'}")

# Exit if missing critical keys
if not OPENAI_API_KEY or not NEWS_API_KEY:
    print("ERROR: Missing API keys. Please set OPENAI_API_KEY and NEWS_API_KEY in your .env file.")
    print("Create or edit .env file with the following:")
    print("OPENAI_API_KEY=your_openai_api_key_here")
    print("NEWS_API_KEY=your_news_api_key_here")

# Email Settings
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "").split(",")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "jvm-tech-news@example.com")
SENDER_NAME = os.getenv("SENDER_NAME", "JVM Tech News Digest")

# News Sources
RSS_SOURCES = [
    # {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    # {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    # {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    # {"name": "Ars Technica", "url": "http://feeds.arstechnica.com/arstechnica/index"},
    # {"name": "Hacker News", "url": "https://news.ycombinator.com/rss"},
    # JVM-specific sources
    {"name": "InfoQ Java", "url": "https://feed.infoq.com/java/"},
    {"name": "Java Code Geeks", "url": "https://www.javacodegeeks.com/feed"},
    {"name": "Baeldung", "url": "https://www.baeldung.com/feed/"},
    {"name": "Spring Blog", "url": "https://spring.io/blog.atom"},
    {"name": "Eclipse Blog", "url": "https://blogs.eclipse.org/blog/feed"},
    {"name": "Inside Java", "url": "https://inside.java/feed.xml"},
    {"name": "jOOQ Blog", "url": "https://blog.jooq.org/feed/"},
    {"name": "Vlad Mihalcea's Blog", "url": "https://vladmihalcea.com/feed/"},
    {"name": "DZone Java", "url": "https://feeds.dzone.com/java"},
    {"name": "JetBrains Blog", "url": "https://blog.jetbrains.com/feed/"}
]

NEWS_API_SOURCES = [
    "the-verge",
    "wired",
    "techcrunch",
    "ars-technica",
    "hacker-news",
]

# Application Settings
MAX_ARTICLES_PER_SOURCE = 10
TOP_ARTICLES_IN_DIGEST = 6
SCHEDULE_INTERVAL_HOURS = 12  # Run every 12 hours
MIN_IMPORTANCE_SCORE = 0.45   # Minimum score to include in digest (lowered from 0.6)
RECENT_ARTICLES_DAYS = 5      # Consider articles from the last 5 days

# Web Crawling Settings
ENABLE_WEB_CRAWLING = False    # Disable web crawling for faster testing
CRAWL_DELAY_MIN = 1.0         # Minimum delay between requests in seconds
CRAWL_DELAY_MAX = 3.0         # Maximum delay between requests in seconds
CRAWL_USER_AGENT = "JVM Tech News Agent/1.0 (Mozilla/5.0 compatible)"

# Ollama Settings (Prioritized)
ENABLE_OLLAMA = True          # Enable Ollama for local LLM processing
OLLAMA_HOST = "http://localhost:11434"  # Ollama API host
OLLAMA_MODEL = "deepseek-r1:7b"  # Using deepseek-r1:7b (Qwen-7B reasoning model)
# Select from available models: llama3, deepseek-r1:7b, mistral, mixtral, phi3:mini, deepseek-coder
# See more models at: https://ollama.com/library
OLLAMA_PRIORITY = True        # Always prioritize Ollama over OpenAI when both are available
OLLAMA_SUMMARIZE_TEMP = 0.2   # Temperature for summarization (lower = more focused)
OLLAMA_RATING_TEMP = 0.1      # Temperature for rating (lower = more consistent)

# LLM Settings
SUMMARY_MAX_LENGTH = 150  # Max length of article summaries in characters 