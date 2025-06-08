"""LLM service for natural language processing tasks."""

import json
import logging
from typing import Any, Dict

from config import settings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from prompts import PromptTemplates

logger = logging.getLogger(__name__)


class LLMService:
    """Service class for LLM interactions."""

    def __init__(self):
        """Initialize LLMService with required configurations."""
        self.llm = self._initialize_llm()
        self.prompts = PromptTemplates()

    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize the LLM client."""
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=settings.llm_temperature,
        )

    def parse_travel_request(
        self,
        user_query: str,
        departure_city: str,
        arrival_city: str,
        departure_range: tuple,
        return_range: tuple,
    ) -> Dict[str, Any]:
        """Parse user travel request and extract optimal parameters."""
        try:
            system_prompt = self.prompts.get_request_parser_prompt(
                departure_city=departure_city,
                arrival_city=arrival_city,
                departure_range=departure_range,
                return_range=return_range,
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=user_query
                    or f"Find flights from {departure_city} to \
                        {arrival_city} given the above conditions."
                ),
            ]

            response = self.llm.invoke(messages)

            # Parse JSON response
            try:
                parsed_data = json.loads(response.content)

                # Validate required fields
                required_fields = [
                    "optimal_departure_date",
                    "optimal_return_date",
                    "reasoning",
                ]
                for field in required_fields:
                    if field not in parsed_data:
                        parsed_data[field] = self._get_default_value(
                            field, departure_range, return_range
                        )

                return parsed_data

            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM JSON response, using fallback")
                return self._get_fallback_parsed_request(departure_range, return_range)

        except Exception as e:
            logger.error(f"Error parsing travel request: {e}")
            return self._get_fallback_parsed_request(departure_range, return_range)

    def format_flight_results(self, flight_data: Dict[str, Any]) -> str:
        """Format flight search results for display."""
        try:
            if not flight_data.get("data"):
                return "No flights found for your search criteria."

            # Simplify data to avoid token limits
            simplified_data = self._simplify_flight_data(flight_data["data"][:5])

            system_prompt = self.prompts.get_results_formatter_prompt()

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=f"Flight Results: {json.dumps(simplified_data, indent=2)}"
                ),
            ]

            response = self.llm.invoke(messages)
            return response.content

        except Exception as e:
            logger.error(f"Error formatting flight results: {e}")
            return self._get_fallback_formatted_results(flight_data)

    def extract_preferences(self, user_query: str) -> Dict[str, Any]:
        """Extract travel preferences from natural language query."""
        try:
            system_prompt = self.prompts.get_preference_extraction_prompt(user_query)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_query),
            ]

            response = self.llm.invoke(messages)

            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                return {"raw_query": user_query, "extracted": False}

        except Exception as e:
            logger.error(f"Error extracting preferences: {e}")
            return {"raw_query": user_query, "error": str(e)}

    def _simplify_flight_data(self, flight_offers: list) -> list:
        """Simplify flight data to essential information."""
        simplified = []

        for i, offer in enumerate(flight_offers):
            simplified_offer = {
                "option": i + 1,
                "price": offer.get("price", {}).get("total", "N/A"),
                "currency": offer.get("price", {}).get("currency", "EUR"),
                "itineraries": [],
            }

            for itinerary in offer.get("itineraries", []):
                itinerary_info = {
                    "duration": itinerary.get("duration", ""),
                    "segments": [],
                }

                for segment in itinerary.get("segments", []):
                    segment_info = {
                        "departure": {
                            "airport": segment.get("departure", {}).get("iataCode", ""),
                            "time": segment.get("departure", {}).get("at", ""),
                        },
                        "arrival": {
                            "airport": segment.get("arrival", {}).get("iataCode", ""),
                            "time": segment.get("arrival", {}).get("at", ""),
                        },
                        "airline": segment.get("carrierCode", ""),
                        "flight_number": segment.get("number", ""),
                        "duration": segment.get("duration", ""),
                    }
                    itinerary_info["segments"].append(segment_info)

                simplified_offer["itineraries"].append(itinerary_info)

            simplified.append(simplified_offer)

        return simplified

    def _get_default_value(
        self, field: str, departure_range: tuple, return_range: tuple
    ) -> str:
        """Get default values for missing fields."""
        defaults = {
            "optimal_departure_date": departure_range[0].strftime("%Y-%m-%d"),
            "optimal_return_date": return_range[0].strftime("%Y-%m-%d"),
            "reasoning": "Using earliest available dates from the specified range",
            "confidence_score": 0.5,
        }

        return defaults.get(field, "")

    def _get_fallback_parsed_request(
        self, departure_range: tuple, return_range: tuple
    ) -> Dict[str, Any]:
        """Generate fallback parsed request when LLM fails."""
        return {
            "optimal_departure_date": departure_range[0].strftime("%Y-%m-%d"),
            "optimal_return_date": return_range[0].strftime("%Y-%m-%d"),
            "reasoning": "Using default dates due to parsing error",
            "confidence_score": 0.3,
            "fallback": True,
        }

    def _get_fallback_formatted_results(self, flight_data: Dict[str, Any]) -> str:
        """Generate basic formatted results when LLM formatting fails."""
        if not flight_data.get("data"):
            return "No flights found."

        results = ["## Flight Options\n"]

        for i, offer in enumerate(flight_data["data"][:3]):
            price = offer.get("price", {})
            results.append(f"### Option {i+1}")
            results.append(
                f"**Price:** {price.get('total', 'N/A')} {price.get('currency', 'EUR')}"
            )
            results.append(f"**Itineraries:** {len(offer.get('itineraries', []))}")
            results.append("")

        return "\n".join(results)
