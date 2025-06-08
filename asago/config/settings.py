"""Configuration management for the Flight Search Assistant."""
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings with validation."""

    openai_api_key: str
    amadeus_api_key: str
    amadeus_api_secret: str

    amadeus_base_url: str = "https://test.api.amadeus.com"
    amadeus_token_url: str = "https://test.api.amadeus.com/v1/security/oauth2/token"
    amadeus_flights_url: str = "https://test.api.amadeus.com/v2/shopping/flight-offers"

    llm_model: str = "gpt-3.5-turbo"
    llm_temperature: float = 0.1

    max_flight_offers: int = 5
    default_currency: str = "EUR"
    cache_ttl: int = 3600  # 1 hour

    page_title: str = "Asago"
    page_header: str = "Asago ✈️ Smart Flight Search Assistant"
    page_icon: str = "✈️"
    layout: str = "wide"

    class Config:
        """Configuration for Pydantic settings."""

        env_file = ".env"
        case_sensitive = False

    @field_validator("openai_api_key", "amadeus_api_key", "amadeus_api_secret")
    def validate_api_keys(cls, v):
        """Validate that API keys are not empty."""
        if not v:
            raise ValueError("API keys cannot be empty")
        return v

    @field_validator("llm_temperature")
    def validate_temperature(cls, v):
        """Validate LLM temperature setting."""
        if not 0 <= v <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        return v


settings = Settings()
