"""
Environment configuration loader.

Loads configuration from .env file and provides type-safe access.
Falls back to sensible defaults if .env is missing.

Usage:
    from utils.env import env
    
    api_key = env.get("OPENAI_API_KEY")
    headless = env.get_bool("BROWSER_HEADLESS", True)
    timeout = env.get_int("BROWSER_TIMEOUT_MS", 30000)
    temperature = env.get_float("EXPLORER_TEMPERATURE", 0.2)
"""

import os
from pathlib import Path
from typing import Optional, Union


class EnvConfig:
    """
    Environment configuration loader.
    
    Loads from .env file if present, otherwise uses os.environ.
    Provides type-safe accessors with fallback defaults.
    """
    
    def __init__(self):
        """Initialize and load .env if present."""
        self._loaded = False
        self._load_dotenv()
    
    def _load_dotenv(self):
        """
        Load .env file using python-dotenv if available.
        
        Gracefully handles missing .env or missing python-dotenv.
        """
        try:
            from dotenv import load_dotenv
            
            # Find .env file (should be in project root)
            project_root = Path(__file__).parent.parent
            env_path = project_root / ".env"
            
            if env_path.exists():
                load_dotenv(env_path)
                self._loaded = True
            else:
                # No .env file, will use os.environ and defaults
                pass
        
        except ImportError:
            # python-dotenv not installed, will use os.environ and defaults
            pass
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get string environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        return os.environ.get(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get boolean environment variable.
        
        Recognizes: true/false, yes/no, 1/0 (case-insensitive)
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Boolean value
        """
        value = os.environ.get(key)
        
        if value is None:
            return default
        
        return value.lower() in ("true", "yes", "1", "on")
    
    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get integer environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found or invalid
            
        Returns:
            Integer value
        """
        value = os.environ.get(key)
        
        if value is None:
            return default
        
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Get float environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found or invalid
            
        Returns:
            Float value
        """
        value = os.environ.get(key)
        
        if value is None:
            return default
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_path(self, key: str, default: Optional[Union[str, Path]] = None) -> Optional[Path]:
        """
        Get path environment variable.
        
        Args:
            key: Environment variable name
            default: Default path if not found
            
        Returns:
            Path object or None
        """
        value = os.environ.get(key)
        
        if value is None:
            return Path(default) if default else None
        
        return Path(value)
    
    def is_loaded(self) -> bool:
        """
        Check if .env file was successfully loaded.
        
        Returns:
            True if .env was found and loaded
        """
        return self._loaded
    
    def require(self, key: str) -> str:
        """
        Get required environment variable.
        
        Raises error if not found.
        
        Args:
            key: Environment variable name
            
        Returns:
            Environment variable value
            
        Raises:
            ValueError: If variable not found
        """
        value = os.environ.get(key)
        
        if value is None or value == "":
            raise ValueError(
                f"Required environment variable '{key}' not found. "
                f"Please set it in .env file or environment."
            )
        
        return value


# Global singleton instance
env = EnvConfig()


# Convenience functions (optional, for backwards compatibility)
def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get string environment variable."""
    return env.get(key, default)


def get_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    return env.get_bool(key, default)


def get_int(key: str, default: int = 0) -> int:
    """Get integer environment variable."""
    return env.get_int(key, default)


def get_float(key: str, default: float = 0.0) -> float:
    """Get float environment variable."""
    return env.get_float(key, default)


def get_path(key: str, default: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """Get path environment variable."""
    return env.get_path(key, default)
