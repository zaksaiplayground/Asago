"""Flight Search Nodes for Asago Graph."""
from asago.models.state import FlightSearchState
from asago.services import amadeus_service, llm_service


class FlightSearchNodes:
    """Nodes for flight search workflow in Asago Graph."""

    def __init__(self):
        """Initialize FlightSearchNodes with required services"""
        self.amadeus_service = amadeus_service.AmadeusService()
        self.llm_service = llm_service.LLMService()
        self.llm = self.llm_service.llm

    def parse_user_request_node(self, state: FlightSearchState) -> FlightSearchState:
        """Parse user request and extract optimal dates"""
        try:
            parsed_data = self.llm_service.parse_travel_request(
                user_query=state['user_query'],
                departure_city=state['departure_city'],
                arrival_city=state['arrival_city'],
                departure_range=state['departure_date_range'],
                return_range=state['return_date_range']
            )

            state['parsed_request'] = parsed_data
            return state
            
        except Exception as e:
            state['error'] = f"Error parsing request: {str(e)}"
            return state

    def search_flights_node(self, state: FlightSearchState) -> FlightSearchState:
        """Search flights using Amadeus API"""
        try:
            # Get dates from parsed request or use defaults
            if state.get('parsed_request'):
                departure_date = state['parsed_request']['optimal_departure_date']
                return_date = state['parsed_request']['optimal_return_date']
            else:
                departure_date = state['departure_date_range'][0].strftime('%Y-%m-%d')
                return_date = state['return_date_range'][0].strftime('%Y-%m-%d')
            
            # Search flights using Amadeus API
            flight_results = self.amadeus_service.search_amadeus_flights(
                state['departure_city'],
                state['arrival_city'],
                departure_date,
                return_date,
                state['adults']
            )
            
            state['flight_results'] = flight_results
            return state
            
        except Exception as e:
            state['error'] = f"Flight search error: {str(e)}"
            return state

    def format_results_node(self, state: FlightSearchState) -> FlightSearchState:
        """Format flight results for display"""
        try:
            if not state.get('flight_results') or not state['flight_results'].get('data'):
                state['formatted_results'] = "No flights found."
                return state
            
            formatted_results = self.llm_service.format_flight_results(state['flight_results'])
            
            state['formatted_results'] = formatted_results
            return state
            
        except Exception as e:
            state['error'] = f"Error formatting results: {str(e)}"
            state['formatted_results'] = "Error formatting flight results."
            return state