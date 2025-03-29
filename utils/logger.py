import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Callable, Any, Optional


def setup_logger(log_dir: str = 'logs', log_level: int = logging.INFO) -> logging.Logger:
    """
    Set up the application logger with console and file handlers.
    
    Args:
        log_dir: Directory to store log files.
        log_level: Logging level (default: INFO).
        
    Returns:
        Configured logger instance.
    """
    # Create the logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create a timestamp for the log file name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'tech_news_agent_{timestamp}.log')
    
    # Create logger
    logger = logging.getLogger('tech_news_agent')
    logger.setLevel(log_level)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # Create file handler (rotating to keep log files manageable)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"Logging setup complete. Log file: {log_file}")
    
    return logger


def safe_exception_handler(
    logger: logging.Logger, 
    message: str, 
    exception: Exception, 
    masking_regex: Optional[str] = None
) -> None:
    """
    Safely log exceptions without exposing sensitive information.
    
    Args:
        logger: Logger instance.
        message: Message to log.
        exception: Exception that was raised.
        masking_regex: Optional regex pattern to mask sensitive data in the error message.
    """
    error_msg = str(exception)
    
    # Mask sensitive data if regex pattern provided
    if masking_regex:
        import re
        error_msg = re.sub(masking_regex, "***MASKED***", error_msg)
    
    # Get traceback but filter out sensitive information
    tb_lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
    filtered_tb = ''.join(tb_lines)
    
    # Log full details to file but only basic info to console
    logger.error(f"{message}: {error_msg}")
    logger.debug(f"Traceback for {message}:\n{filtered_tb}")


def safe_execution(
    logger: logging.Logger, 
    func: Callable, 
    error_message: str, 
    masking_regex: Optional[str] = None, 
    *args, 
    **kwargs
) -> Optional[Any]:
    """
    Execute a function safely and handle exceptions properly.
    
    Args:
        logger: Logger instance.
        func: Function to execute.
        error_message: Message to log if an exception occurs.
        masking_regex: Optional regex pattern to mask sensitive data in error logs.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.
        
    Returns:
        The function result or None if an exception occurred.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        safe_exception_handler(logger, error_message, e, masking_regex)
        return None 