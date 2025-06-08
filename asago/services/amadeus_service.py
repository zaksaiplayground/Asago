"""Amadeus Service for flight search using Amadeus API."""
import requests  # type: ignore[import-untyped]
import streamlit as st

from asago.config import settings


class AmadeusService:
    """Service class for interacting with Amadeus API for flight search."""

    def __init__(self):
        """Initialize AmadeusService."""
        self.base_url = settings.amadeus_token_url
        self.flights_url = settings.amadeus_flights_url
        self.api_key = settings.amadeus_api_key
        self.api_secret = settings.amadeus_api_secret
        self.token = self._get_access_token(
            self.api_key, self.api_secret, self.base_url
        )

    @staticmethod
    @st.cache_data(ttl=settings.cache_ttl)  # Cache token for 1 hour
    def _get_access_token(api_key, api_secret, base_url):
        """Get Amadeus API access token."""
        try:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": api_secret,
            }

            response = requests.post(base_url, headers=headers, data=data)
            response.raise_for_status()

            return response.json()["access_token"]
        except Exception as e:
            raise Exception(f"Failed to get Amadeus token: {str(e)}")

    def search_amadeus_flights(
        self, origin, destination, departure_date, return_date, adults=1
    ):
        """Search flights using Amadeus API directly."""
        try:

            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }

            body = {
                "currencyCode": "EUR",
                "originDestinations": [
                    {
                        "id": "1",
                        "originLocationCode": origin,
                        "destinationLocationCode": destination,
                        "departureDateTimeRange": {"date": departure_date},
                    },
                    {
                        "id": "2",
                        "originLocationCode": destination,
                        "destinationLocationCode": origin,
                        "departureDateTimeRange": {"date": return_date},
                    },
                ],
                "searchCriteria": {
                    "maxFlightOffers": 5,
                    "flightFilters": {
                        "carrierRestrictions": {
                            "includedCarrierCodes": ["EK"]
                        }  # Example preferred airlines
                    },
                    "nonStop": True,  # Only direct flights
                },
                "travelers": [
                    {"id": str(i + 1), "travelerType": "ADULT"} for i in range(adults)
                ],
                "sources": ["GDS"],
            }

            response = requests.post(self.flights_url, headers=headers, json=body)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            raise Exception(f"Flight search error: {str(e)}")
