"""State model for flight search application."""

from typing import Any, List, TypedDict


class FlightSearchState(TypedDict):
    """State model for flight search application."""

    user_query: str
    departure_city: str
    arrival_city: str
    departure_date_range: tuple
    return_date_range: tuple
    adults: int
    parsed_request: dict
    flight_results: List[Any]
    formatted_results: str
    error: str
