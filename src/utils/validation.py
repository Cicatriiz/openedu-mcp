"""
Input validation utilities for OpenEdu MCP Server.

This module provides validation functions for user inputs, API parameters,
and data integrity checks.
"""

import re
from typing import Any, List, Optional, Dict, Union
from datetime import datetime, date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exceptions import ValidationError
from models.base import GradeLevel, CurriculumStandard, Subject


class Validator:
    """Input validation utility class."""
    
    @staticmethod
    def validate_query(query: str, min_length: int = 1, max_length: int = 500) -> str:
        """
        Validate search query string.
        
        Args:
            query: Query string to validate
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            
        Returns:
            Cleaned query string
            
        Raises:
            ValidationError: If query is invalid
        """
        if not isinstance(query, str):
            raise ValidationError("Query must be a string", "query")
        
        # Strip whitespace
        query = query.strip()
        
        if len(query) < min_length:
            raise ValidationError(
                f"Query must be at least {min_length} characters long",
                "query"
            )
        
        if len(query) > max_length:
            raise ValidationError(
                f"Query must be no more than {max_length} characters long",
                "query"
            )
        
        # Check for potentially harmful content
        if re.search(r'[<>"\']', query):
            raise ValidationError(
                "Query contains invalid characters",
                "query"
            )
        
        return query
    
    @staticmethod
    def validate_grade_level(grade_level: str) -> GradeLevel:
        """
        Validate and convert grade level string.
        
        Args:
            grade_level: Grade level string
            
        Returns:
            GradeLevel enum value
            
        Raises:
            ValidationError: If grade level is invalid
        """
        if not isinstance(grade_level, str):
            raise ValidationError("Grade level must be a string", "grade_level")
        
        grade_level = grade_level.strip()
        
        # Try to find matching grade level
        for gl in GradeLevel:
            if gl.value.lower() == grade_level.lower():
                return gl
        
        # Try common variations
        grade_level_lower = grade_level.lower()
        if grade_level_lower in ["k", "kindergarten", "k-2", "k2"]:
            return GradeLevel.K_2
        elif grade_level_lower in ["elementary", "3-5", "35"]:
            return GradeLevel.GRADES_3_5
        elif grade_level_lower in ["middle", "6-8", "68"]:
            return GradeLevel.GRADES_6_8
        elif grade_level_lower in ["high", "high school", "9-12", "912"]:
            return GradeLevel.GRADES_9_12
        elif grade_level_lower in ["college", "university", "higher ed"]:
            return GradeLevel.COLLEGE
        
        valid_levels = [gl.value for gl in GradeLevel]
        raise ValidationError(
            f"Invalid grade level. Must be one of: {', '.join(valid_levels)}",
            "grade_level"
        )
    
    @staticmethod
    def validate_subject(subject: str) -> str:
        """
        Validate educational subject.
        
        Args:
            subject: Subject string
            
        Returns:
            Validated subject string
            
        Raises:
            ValidationError: If subject is invalid
        """
        if not isinstance(subject, str):
            raise ValidationError("Subject must be a string", "subject")
        
        subject = subject.strip()
        
        if len(subject) < 2:
            raise ValidationError("Subject must be at least 2 characters long", "subject")
        
        if len(subject) > 100:
            raise ValidationError("Subject must be no more than 100 characters long", "subject")
        
        # Check for valid characters (letters, spaces, hyphens)
        if not re.match(r'^[a-zA-Z\s\-&]+$', subject):
            raise ValidationError("Subject contains invalid characters", "subject")
        
        return subject.title()  # Convert to title case
    
    @staticmethod
    def validate_limit(limit: int, min_limit: int = 1, max_limit: int = 100) -> int:
        """
        Validate result limit parameter.
        
        Args:
            limit: Limit value
            min_limit: Minimum allowed limit
            max_limit: Maximum allowed limit
            
        Returns:
            Validated limit
            
        Raises:
            ValidationError: If limit is invalid
        """
        if not isinstance(limit, int):
            raise ValidationError("Limit must be an integer", "limit")
        
        if limit < min_limit:
            raise ValidationError(f"Limit must be at least {min_limit}", "limit")
        
        if limit > max_limit:
            raise ValidationError(f"Limit must be no more than {max_limit}", "limit")
        
        return limit
    
    @staticmethod
    def validate_isbn(isbn: str) -> str:
        """
        Validate ISBN format.
        
        Args:
            isbn: ISBN string
            
        Returns:
            Cleaned ISBN string
            
        Raises:
            ValidationError: If ISBN is invalid
        """
        if not isinstance(isbn, str):
            raise ValidationError("ISBN must be a string", "isbn")
        
        # Remove hyphens and spaces
        isbn = re.sub(r'[-\s]', '', isbn)
        
        # Check length and format
        if len(isbn) == 10:
            # ISBN-10 validation
            if not re.match(r'^\d{9}[\dX]$', isbn):
                raise ValidationError("Invalid ISBN-10 format", "isbn")
        elif len(isbn) == 13:
            # ISBN-13 validation
            if not re.match(r'^\d{13}$', isbn):
                raise ValidationError("Invalid ISBN-13 format", "isbn")
        else:
            raise ValidationError("ISBN must be 10 or 13 digits", "isbn")
        
        return isbn
    
    @staticmethod
    def validate_language_code(language: str) -> str:
        """
        Validate language code.
        
        Args:
            language: Language code
            
        Returns:
            Validated language code
            
        Raises:
            ValidationError: If language code is invalid
        """
        if not isinstance(language, str):
            raise ValidationError("Language must be a string", "language")
        
        language = language.lower().strip()
        
        # Common language codes
        valid_languages = {
            'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko',
            'ar', 'hi', 'nl', 'sv', 'no', 'da', 'fi', 'pl', 'tr', 'he'
        }
        
        if language not in valid_languages:
            raise ValidationError(
                f"Unsupported language code: {language}",
                "language"
            )
        
        return language
    
    @staticmethod
    def validate_date_range(
        start_date: Optional[Union[str, date]], 
        end_date: Optional[Union[str, date]]
    ) -> tuple[Optional[date], Optional[date]]:
        """
        Validate date range.
        
        Args:
            start_date: Start date (string or date object)
            end_date: End date (string or date object)
            
        Returns:
            Tuple of validated dates
            
        Raises:
            ValidationError: If date range is invalid
        """
        def parse_date(date_val: Union[str, date, None]) -> Optional[date]:
            if date_val is None:
                return None
            
            if isinstance(date_val, date):
                return date_val
            
            if isinstance(date_val, str):
                try:
                    return datetime.fromisoformat(date_val).date()
                except ValueError:
                    try:
                        return datetime.strptime(date_val, '%Y-%m-%d').date()
                    except ValueError:
                        raise ValidationError(f"Invalid date format: {date_val}", "date")
            
            raise ValidationError("Date must be a string or date object", "date")
        
        parsed_start = parse_date(start_date)
        parsed_end = parse_date(end_date)
        
        if parsed_start and parsed_end:
            if parsed_start > parsed_end:
                raise ValidationError("Start date must be before end date", "date_range")
            
            # Check for reasonable date range (not more than 10 years)
            if (parsed_end - parsed_start).days > 3650:
                raise ValidationError("Date range too large (max 10 years)", "date_range")
        
        return parsed_start, parsed_end
    
    @staticmethod
    def validate_email(email: str) -> str:
        """
        Validate email address format.
        
        Args:
            email: Email address
            
        Returns:
            Validated email address
            
        Raises:
            ValidationError: If email is invalid
        """
        if not isinstance(email, str):
            raise ValidationError("Email must be a string", "email")
        
        email = email.strip().lower()
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format", "email")
        
        if len(email) > 254:  # RFC 5321 limit
            raise ValidationError("Email address too long", "email")
        
        return email
    
    @staticmethod
    def validate_url(url: str) -> str:
        """
        Validate URL format.
        
        Args:
            url: URL string
            
        Returns:
            Validated URL
            
        Raises:
            ValidationError: If URL is invalid
        """
        if not isinstance(url, str):
            raise ValidationError("URL must be a string", "url")
        
        url = url.strip()
        
        # Basic URL validation
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        
        if not re.match(url_pattern, url):
            raise ValidationError("Invalid URL format", "url")
        
        if len(url) > 2048:  # Common URL length limit
            raise ValidationError("URL too long", "url")
        
        return url
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 10000) -> str:
        """
        Sanitize text input by removing potentially harmful content.
        
        Args:
            text: Text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
            
        Raises:
            ValidationError: If text is invalid
        """
        if not isinstance(text, str):
            raise ValidationError("Text must be a string", "text")
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Limit length
        if len(text) > max_length:
            raise ValidationError(f"Text too long (max {max_length} characters)", "text")
        
        return text.strip()
    
    @staticmethod
    def validate_search_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a dictionary of search parameters.
        
        Args:
            params: Dictionary of parameters to validate
            
        Returns:
            Dictionary of validated parameters
            
        Raises:
            ValidationError: If any parameter is invalid
        """
        validated = {}
        
        for key, value in params.items():
            if key == "query" and value is not None:
                validated[key] = Validator.validate_query(str(value))
            elif key == "grade_level" and value is not None:
                grade_level = Validator.validate_grade_level(str(value))
                validated[key] = grade_level.value if hasattr(grade_level, 'value') else grade_level
            elif key == "subject" and value is not None:
                validated[key] = Validator.validate_subject(str(value))
            elif key == "limit" and value is not None:
                validated[key] = Validator.validate_limit(int(value))
            elif key == "language" and value is not None:
                validated[key] = Validator.validate_language_code(str(value))
            elif key in ["isbn", "isbn10", "isbn13"] and value is not None:
                validated[key] = Validator.validate_isbn(str(value))
            elif key == "url" and value is not None:
                validated[key] = Validator.validate_url(str(value))
            elif key == "email" and value is not None:
                validated[key] = Validator.validate_email(str(value))
            else:
                # For other parameters, just ensure they're reasonable
                if isinstance(value, str):
                    validated[key] = Validator.sanitize_text(value)
                else:
                    validated[key] = value
        
        return validated