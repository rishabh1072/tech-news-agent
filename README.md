# Tech News Agent

An AI-powered tech news aggregator that collects, summarizes, and rates tech news articles, delivering the most important updates via email.

## Features

- Fetches tech news from multiple sources
- AI-powered summarization of articles
- Importance rating based on impact and relevance
- Email delivery of curated tech news digest
- Configurable sources and update frequency

## Project Structure

```
tech-news-agent/
├── config/             # Configuration settings
├── sources/            # News source connectors
├── processors/         # Article processing modules
├── delivery/           # Email and notification services
├── models/             # Data models
├── utils/              # Utility functions
├── main.py             # Application entry point
└── requirements.txt    # Dependencies
```

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Configure settings in `config/settings.py`
6. Run the application: `python main.py`

## Configuration

Create a `.env` file with the following variables:
```
OPENAI_API_KEY=your_openai_api_key
NEWS_API_KEY=your_news_api_key
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USERNAME=your_email@example.com
EMAIL_PASSWORD=your_email_password
``` 