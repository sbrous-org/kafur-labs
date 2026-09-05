import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration for the travel bot, loaded from environment."""

    # LLM Configuration
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "claude")

    # Map provider to API key env var
    if LLM_PROVIDER == "claude":
        LLM_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    elif LLM_PROVIDER == "openrouter":
        LLM_API_KEY = os.getenv("OPENROUTER_API_KEY")
    else:  # openai
        LLM_API_KEY = os.getenv("OPENAI_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL")  # Optional: override default model
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "500"))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # Weather API
    WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

    # Application
    ENV = os.getenv("ENV", "production")
    DEBUG = ENV == "development"

    @staticmethod
    def get_llm_config() -> Dict[str, Any]:
        """Get LLM provider configuration as a dict."""
        config = {
            "provider": Config.LLM_PROVIDER,
            "api_key": Config.LLM_API_KEY,
        }

        if Config.LLM_MODEL:
            config["model"] = Config.LLM_MODEL

        if not config["api_key"]:
            raise ValueError(
                f"API key not found for LLM provider '{Config.LLM_PROVIDER}'. "
                f"Set ANTHROPIC_API_KEY (for claude) or OPENAI_API_KEY (for openai) "
                f"in your .env file."
            )

        return config

    @staticmethod
    def validate():
        """Validate that all required config is present."""
        try:
            Config.get_llm_config()
        except ValueError as e:
            print(f"⚠️  Configuration error: {e}")
            raise
