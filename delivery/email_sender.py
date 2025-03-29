import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional
from datetime import datetime
import os

from config.settings import EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_RECIPIENTS, SENDER_EMAIL, SENDER_NAME
from models.article import Article

logger = logging.getLogger(__name__)


class EmailSender:
    """Sends tech news digests via email."""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        recipients: Optional[List[str]] = None,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None
    ):
        """
        Initialize the email sender.
        
        Args:
            host: SMTP host. If None, uses the host from settings.
            port: SMTP port. If None, uses the port from settings.
            username: Email username. If None, uses the username from settings.
            password: Email password. If None, uses the password from settings.
            recipients: List of email recipients. If None, uses the recipients from settings.
            sender_email: Email address to send from. If None, uses the username from settings.
            sender_name: Name to display as sender. If None, uses "JVM Tech News Digest".
        """
        self.host = host or EMAIL_HOST
        self.port = port or EMAIL_PORT
        self.username = username or EMAIL_USERNAME
        self.password = password or EMAIL_PASSWORD
        
        if not all([self.host, self.port, self.username, self.password]):
            raise ValueError("Email configuration is incomplete")
        
        self.recipients = recipients or EMAIL_RECIPIENTS
        if not self.recipients:
            raise ValueError("No email recipients specified")
            
        # Set sender information
        self.sender_email = sender_email or SENDER_EMAIL
        self.sender_name = sender_name or SENDER_NAME
    
    def send_digest(self, articles: List[Article], subject: Optional[str] = None) -> bool:
        """
        Send a tech news digest email.
        
        Args:
            articles: List of Article objects to include in the digest.
            subject: Email subject. If None, a default subject is generated.
            
        Returns:
            True if the email was sent successfully, False otherwise.
        """
        if not articles:
            logger.warning("No articles provided for digest email")
            return False
        
        # Debug email settings to help troubleshooting
        logger.info(f"Email settings: HOST={self.host}, PORT={self.port}, USERNAME={self.username[:4]}..., SENDER={self.sender_email}")
        logger.info(f"Recipients: {', '.join(self.recipients)}")
        
        # Sort articles by importance score in descending order
        sorted_articles = sorted(articles, key=lambda x: x.importance_score or 0, reverse=True)
        
        # Create the email message
        msg = MIMEMultipart('alternative')
        # Format the From header with name and email
        msg['From'] = f"{self.sender_name} <{self.sender_email}>"
        msg['To'] = ', '.join(self.recipients)
        
        # Set the subject
        if not subject:
            date_str = datetime.now().strftime('%Y-%m-%d')
            subject = f"JVM Tech News Digest - {date_str}"
        msg['Subject'] = subject
        
        # Generate plain text content as fallback
        try:
            text_content = self._create_text_content(sorted_articles)
            logger.info(f"Generated text content: {len(text_content)} characters")
            
            # Generate simple HTML content
            html_content = self._create_simple_html_content(sorted_articles)
            logger.info(f"Generated HTML content: {len(html_content)} characters")
            
            # Attach both versions (text first as fallback, then HTML)
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
        except Exception as e:
            logger.error(f"Error generating email content: {e}")
            return False
        
        # Send the email with better error handling
        try:
            logger.info(f"Connecting to SMTP server at {self.host}:{self.port}")
            
            # Try with SMTP_SSL first (especially for Yahoo)
            try:
                server = smtplib.SMTP_SSL(self.host, self.port)
                logger.info("Connected using SMTP_SSL")
            except Exception as ssl_err:
                logger.info(f"SMTP_SSL connection failed: {ssl_err}. Trying regular SMTP with TLS...")
                server = smtplib.SMTP(self.host, self.port)
                server.set_debuglevel(1)  # Enable verbose debug output
                server.ehlo()  # Identify to the SMTP server
                
                # Check if starttls is available
                if server.has_extn('STARTTLS'):
                    logger.info("Starting TLS")
                    server.starttls()
                    server.ehlo()  # Re-identify over TLS connection
                else:
                    logger.warning("STARTTLS not available on server")
            
            logger.info(f"Logging in as {self.username}")
            server.login(self.username, self.password)
            
            logger.info("Sending email message")
            server.send_message(msg)
            
            logger.info("Closing connection")
            server.quit()
            
            logger.info(f"Successfully sent tech news digest to {len(self.recipients)} recipients")
            return True
        except smtplib.SMTPAuthenticationError as auth_err:
            logger.error(f"Authentication failed: {auth_err}. Check your username and password. For Yahoo, use an app-specific password instead of your regular password.")
            return False
        except smtplib.SMTPConnectError as conn_err:
            logger.error(f"Connection error: {conn_err}. Check if the SMTP server address is correct and if your network allows SMTP connections.")
            return False
        except smtplib.SMTPServerDisconnected as disc_err:
            logger.error(f"Server disconnected: {disc_err}. The server unexpectedly closed the connection.")
            return False
        except smtplib.SMTPException as smtp_err:
            logger.error(f"SMTP error: {smtp_err}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
            
    def _create_simple_html_content(self, articles: List[Article]) -> str:
        """
        Create simplified HTML content for email digest with minimal styling.
        
        Args:
            articles: List of Article objects.
            
        Returns:
            HTML content.
        """
        # Use a very simple HTML structure with minimal styling to avoid format issues
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>JVM Tech News Digest</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #0078d4; color: white; padding: 20px; text-align: center;">
        <h1>JVM Tech News Digest</h1>
        <p>{datetime.now().strftime('%A, %B %d, %Y')}</p>
    </div>
    
    <div style="padding: 20px;">
"""
        
        # Add each article
        for i, article in enumerate(articles):
            # Clean the summary
            if not article.summary or "<think>" in article.summary:
                summary = "View the full article for details"
            else:
                summary = article.summary
                
            # Format the date
            formatted_date = article.published_date.strftime('%Y-%m-%d') if article.published_date else "Unknown date"
            
            # Format importance score
            importance = "N/A"
            if article.importance_score is not None:
                importance = f"{article.importance_score:.1f}"
            
            # Add article HTML with minimal styling
            html += f"""
        <div style="margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #eee;">
            <h2 style="color: #0078d4; margin-bottom: 5px;">
                {i+1}. <a href="{article.url}" style="color: #0078d4;">{article.title}</a>
            </h2>
            <div style="color: #666; font-size: 0.9em; margin-bottom: 10px;">
                <strong>Source:</strong> {article.source_name} | 
                <strong>Published:</strong> {formatted_date} | 
                <strong>Importance:</strong> {importance}
            </div>
            <p>{summary}</p>
        </div>
"""
        
        # Close HTML structure
        html += """
    </div>
    
    <div style="background-color: #f4f4f4; padding: 15px; text-align: center; font-size: 0.8em; color: #666;">
        <p>This digest was automatically generated by Tech News Agent.</p>
    </div>
</body>
</html>
"""
        
        return html
    
    def _create_text_content(self, articles: List[Article]) -> str:
        """
        Create plain text content for email digest.
        
        Args:
            articles: List of Article objects.
            
        Returns:
            Plain text content.
        """
        text = f"JVM TECH NEWS DIGEST - {datetime.now().strftime('%A, %B %d, %Y')}\n"
        text += "=" * 70 + "\n\n"
        
        for i, article in enumerate(articles):
            # Clean and sanitize the summary
            if not article.summary or "<think>" in article.summary:
                summary = "View the full article for details"
            else:
                summary = article.summary
                
            # Format the date
            formatted_date = article.published_date.strftime('%Y-%m-%d') if article.published_date else "Unknown date"
            
            # Format importance score
            importance = "N/A"
            if article.importance_score is not None:
                importance = f"{article.importance_score:.1f}"
            
            # Add article to text
            text += f"{i+1}. {article.title}\n"
            text += f"   Source: {article.source_name}\n"
            text += f"   Published: {formatted_date}\n"
            text += f"   Importance: {importance}\n"
            text += f"   URL: {article.url}\n"
            text += f"   Summary: {summary}\n\n"
            text += "-" * 50 + "\n\n"
        
        text += "\nThis digest was automatically generated by Tech News Agent.\n"
        return text 