import re
import logging
from datetime import datetime, timedelta
import pytz
import os
from dateutil import parser
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_unique_id():
    """Generate a unique ID for resources."""
    return str(uuid.uuid4())

def parse_datetime(date_string):
    """Parse a date string into a datetime object."""
    try:
        dt = parser.parse(date_string)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)  # Assume UTC if no timezone
        return dt
    except Exception as e:
        logger.error(f"Error parsing date string: {e}")
        return None

def format_datetime(dt, format_str="%Y-%m-%d %H:%M:%S"):
    """Format a datetime object as a string."""
    if not dt:
        return ""
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt.strftime(format_str)
    except Exception as e:
        logger.error(f"Error formatting datetime: {e}")
        return ""

def extract_email_addresses(text):
    """Extract email addresses from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)

def extract_dates(text):
    """Extract date references from text."""
    # This is a simplified implementation
    # In a real app, you'd use a more sophisticated NLP approach
    date_patterns = [
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b',
        r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
        r'\b\d{4}-\d{2}-\d{2}\b',
        r'\b(?:today|tomorrow|yesterday)\b',
        r'\b(?:next|this|last)\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|week|month|year)\b'
    ]
    
    results = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        results.extend(matches)
    
    return results

def extract_time_ranges(text):
    """Extract time ranges from text."""
    # This is a simplified implementation
    time_range_pattern = r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*(?:to|-)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)\b'
    return re.findall(time_range_pattern, text, re.IGNORECASE)

def sanitize_filename(filename):
    """Sanitize a filename to be safe for file systems."""
    # Remove invalid characters
    sanitized = re.sub(r'[^\w\s.-]', '', filename)
    # Replace spaces with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    return sanitized

def truncate_text(text, max_length=100):
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def get_mime_type(file_extension):
    """Get MIME type based on file extension."""
    extension_map = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xls': 'application/vnd.ms-excel',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'ppt': 'application/vnd.ms-powerpoint',
        'txt': 'text/plain',
        'html': 'text/html',
        'csv': 'text/csv',
        'json': 'application/json',
        'xml': 'application/xml',
        'zip': 'application/zip'
    }
    
    ext = file_extension.lower().lstrip('.')
    return extension_map.get(ext, 'application/octet-stream')

def calculate_date_from_natural_language(text):
    """Calculate a date from natural language references."""
    text = text.lower()
    today = datetime.now()
    
    if 'today' in text:
        return today
    elif 'tomorrow' in text:
        return today + timedelta(days=1)
    elif 'yesterday' in text:
        return today - timedelta(days=1)
    
    # Handle "next Tuesday", "this Friday", etc.
    days = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 
        'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    for day_name, day_num in days.items():
        if f"next {day_name}" in text:
            days_ahead = day_num - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        
        if f"this {day_name}" in text:
            days_ahead = day_num - today.weekday()
            if days_ahead < 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
    
    return None

def extract_keywords(text, min_word_length=3, max_keywords=10):
    """Extract important keywords from text."""
    # This is a simple implementation
    # In a real app, you'd use a more sophisticated NLP approach
    
    # Remove punctuation and convert to lowercase
    clean_text = re.sub(r'[^\w\s]', '', text.lower())
    
    # Split into words
    words = clean_text.split()
    
    # Filter short words and common stop words
    stop_words = {
        'the', 'and', 'is', 'in', 'it', 'to', 'of', 'for', 'with', 
        'on', 'at', 'from', 'by', 'about', 'as', 'an', 'are', 'was',
        'were', 'that', 'this', 'these', 'those', 'be', 'been', 'being'
    }
    
    filtered_words = [word for word in words if len(word) >= min_word_length and word not in stop_words]
    
    # Count occurrences
    word_counts = {}
    for word in filtered_words:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    # Sort by frequency
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Return top keywords
    return [word for word, count in sorted_words[:max_keywords]]
