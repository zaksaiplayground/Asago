import streamlit as st
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict, List, Any, Annotated
import os
import requests
import json
from datetime import datetime, timedelta

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Smart Flight Search Assistant",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Smart Flight Search Assistant (LangGraph Version)")

# State definition for LangGraph
class FlightSearchState(TypedDict):
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

# Amadeus API functions
@st.cache_data(ttl=3600)  # Cache token for 1 hour
def get_amadeus_token():
    """Get Amadeus API access token"""
    try:
        url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": os.getenv('AMADEUS_API_KEY'),
            "client_secret": os.getenv('AMADEUS_API_SECRET')
        }
        
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        return response.json()["access_token"]
    except Exception as e:
        raise Exception(f"Failed to get Amadeus token: {str(e)}")

def search_amadeus_flights(origin, destination, departure_date, return_date, adults=1):
    """Search flights using Amadeus API directly"""
    try:
        token = get_amadeus_token()
        
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        body = {
            "currencyCode": "EUR",
            "originDestinations": [
                {
                    "id": "1",
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "departureDateTimeRange": {"date": departure_date}
                },
                {
                    "id": "2", 
                    "originLocationCode": destination,
                    "destinationLocationCode": origin,
                    "departureDateTimeRange": {"date": return_date}
                }
            ],
            "searchCriteria": {
                "maxFlightOffers": 5,
                "flightFilters": {
                    "carrierRestrictions":
                        {"includedCarrierCodes": ["EK"]}  # Example preferred airlines
                },
                "nonStop": True  # Only direct flights
            },
            "travelers": [{"id": str(i+1), "travelerType": "ADULT"} for i in range(adults)],
            "sources": ["GDS"],
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        raise Exception(f"Flight search error: {str(e)}")

@st.cache_resource
def initialize_llm():
    """Initialize LLM"""
    return ChatOpenAI(
        model="gpt-3.5-turbo",
        api_key=os.getenv('OPENAI_API_KEY'),
        temperature=0.1
    )

# Node functions for LangGraph
def parse_user_request_node(state: FlightSearchState) -> FlightSearchState:
    """Parse user request and extract optimal dates"""
    try:
        llm = initialize_llm()
        
        system_message = SystemMessage(content=f"""
        You are a flight booking assistant. Parse this travel request and provide optimal flight search parameters.
        
        CONSTRAINTS:
        - Travel FROM {state['departure_city']} TO {state['arrival_city']}
        - Departure between {state['departure_date_range'][0]} and {state['departure_date_range'][1]}
        - Return between {state['return_date_range'][0]} and {state['return_date_range'][1]}
        - Preferred airlines
        - Number of adults, children, infants
        - Direct flights only if specified
        - And any other preferences mentioned in the user query
        - Departure must be before return date
        
        Respond with JSON containing:
        - optimal_departure_date (YYYY-MM-DD)
        - optimal_return_date (YYYY-MM-DD)
        - reasoning (brief explanation considering user preferences)
        """)
        
        human_message = HumanMessage(content=state['user_query'])
        
        response = llm.invoke([system_message, human_message])
        
        # Parse the JSON response
        try:
            parsed_request = json.loads(response.content)
        except:
            # Fallback if JSON parsing fails
            parsed_request = {
                'optimal_departure_date': state['departure_date_range'][0].strftime('%Y-%m-%d'),
                'optimal_return_date': state['return_date_range'][0].strftime('%Y-%m-%d'),
                'reasoning': 'Using default dates from range'
            }
        
        state['parsed_request'] = parsed_request
        return state
        
    except Exception as e:
        state['error'] = f"Error parsing request: {str(e)}"
        return state

def search_flights_node(state: FlightSearchState) -> FlightSearchState:
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
        flight_results = search_amadeus_flights(
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

def format_results_node(state: FlightSearchState) -> FlightSearchState:
    """Format flight results for display"""
    try:
        llm = initialize_llm()
        
        if not state.get('flight_results') or not state['flight_results'].get('data'):
            state['formatted_results'] = "No flights found."
            return state
        
        # Extract first few flight offers to avoid token limits
        flight_offers = state['flight_results']['data'][:5]
        simplified_data = []
        
        for i, offer in enumerate(flight_offers):
            simplified_offer = {
                'option': i + 1,
                'price': offer.get('price', {}).get('total', 'N/A'),
                'currency': offer.get('price', {}).get('currency', 'EUR'),
                'itineraries': []
            }
            
            for itinerary in offer.get('itineraries', []):
                itinerary_info = {
                    'duration': itinerary.get('duration', ''),
                    'segments': []
                }
                
                for segment in itinerary.get('segments', []):
                    segment_info = {
                        'departure': {
                            'airport': segment.get('departure', {}).get('iataCode', ''),
                            'time': segment.get('departure', {}).get('at', ''),
                        },
                        'arrival': {
                            'airport': segment.get('arrival', {}).get('iataCode', ''),
                            'time': segment.get('arrival', {}).get('at', ''),
                        },
                        'airline': segment.get('carrierCode', ''),
                        'flight_number': segment.get('number', ''),
                        'duration': segment.get('duration', '')
                    }
                    itinerary_info['segments'].append(segment_info)
                
                simplified_offer['itineraries'].append(itinerary_info)
            
            simplified_data.append(simplified_offer)
        
        system_message = SystemMessage(content="""
        Format these flight search results into a clear, readable format for travelers.
        
        For each flight option:
        - Show price prominently with option number
        - Show OUTBOUND journey (first itinerary) and RETURN journey (second itinerary) separately
        - For connecting flights, show all segments with connection airports clearly
        - Include departure/arrival times and dates
        - Show total journey duration for each direction
        - Highlight airline codes and flight numbers
        - Make connections obvious (e.g., "Connection in DXB")
        
        Use markdown formatting for better readability.
        """)
        
        human_message = HumanMessage(content=f"Flight Results: {json.dumps(simplified_data, indent=2)}")
        
        response = llm.invoke([system_message, human_message])
        
        state['formatted_results'] = response.content
        return state
        
    except Exception as e:
        state['error'] = f"Error formatting results: {str(e)}"
        state['formatted_results'] = "Error formatting flight results."
        return state

def create_flight_search_graph():
    """Create LangGraph workflow for flight search"""
    
    # Create the graph
    workflow = StateGraph(FlightSearchState)
    
    # Add nodes
    workflow.add_node("parse_request", parse_user_request_node)
    workflow.add_node("search_flights", search_flights_node)
    workflow.add_node("format_results", format_results_node)
    
    # Add edges
    workflow.set_entry_point("parse_request")
    workflow.add_edge("parse_request", "search_flights")
    workflow.add_edge("search_flights", "format_results")
    workflow.add_edge("format_results", END)
    
    return workflow.compile()

# Streamlit UI
def main():
    # Initialize the graph
    if 'flight_graph' not in st.session_state:
        st.session_state.flight_graph = create_flight_search_graph()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Flight Search Form")
        
        # Basic flight information
        col1_1, col1_2 = st.columns(2)
        
        with col1_1:
            departure_city = st.text_input("Departure City (Airport Code)", placeholder="e.g., BLR, NYC")
            
        with col1_2:
            arrival_city = st.text_input("Arrival City (Airport Code)", placeholder="e.g., MUC, PAR")
        
        # Date ranges
        col2_1, col2_2 = st.columns(2)
        
        with col2_1:
            st.subheader("Departure Date Range")
            departure_start = st.date_input("Earliest Departure", datetime.now() + timedelta(days=7))
            departure_end = st.date_input("Latest Departure", datetime.now() + timedelta(days=30))
            
        with col2_2:
            st.subheader("Return Date Range")
            return_start = st.date_input("Earliest Return", datetime.now() + timedelta(days=14))
            return_end = st.date_input("Latest Return", datetime.now() + timedelta(days=37))
        
        # Number of passengers
        adults = st.number_input("Number of Adult Passengers", min_value=1, max_value=9, value=1)
        
        # User request
        user_request = st.text_area(
            "Describe your travel preferences or requirements:",
            placeholder="e.g., I want to attend Oktoberfest in Munich, need direct flights only, prefer Lufthansa",
            height=100
        )
    
    with col2:
        st.header("Search Assistant")
        
        if st.button("🔍 Search Flights", type="primary"):
            if not departure_city or not arrival_city:
                st.error("Please enter both departure and arrival cities")
                return
                
            if not all([os.getenv('OPENAI_API_KEY'), os.getenv('AMADEUS_API_KEY'), os.getenv('AMADEUS_API_SECRET')]):
                st.error("Please ensure all API keys are set in environment variables")
                return
            
            # Create initial state
            initial_state = FlightSearchState(
                user_query=user_request or f"Find flights from {departure_city} to {arrival_city}",
                departure_city=departure_city,
                arrival_city=arrival_city,
                departure_date_range=(departure_start, departure_end),
                return_date_range=(return_start, return_end),
                adults=adults,
                parsed_request={},
                flight_results=[],
                formatted_results="",
                error=""
            )
            
            # Execute the graph
            with st.spinner("Searching for flights..."):
                try:
                    final_state = st.session_state.flight_graph.invoke(initial_state)
                    
                    if final_state.get('error'):
                        st.error(final_state['error'])
                    else:
                        # Show parsed request info
                        if final_state.get('parsed_request'):
                            st.success("✅ Request analyzed successfully!")
                            parsed = final_state['parsed_request']
                            if 'optimal_departure_date' in parsed:
                                st.info(f"**Suggested dates:** {parsed['optimal_departure_date']} to {parsed['optimal_return_date']}")
                            if 'reasoning' in parsed:
                                st.info(f"**Reasoning:** {parsed['reasoning']}")
                        
                        # Show flight results
                        if final_state.get('formatted_results'):
                            st.success("✅ Flights found!")
                            st.markdown("## Flight Options")
                            st.markdown(final_state['formatted_results'])
                        else:
                            st.warning("No flights found for the specified criteria.")
                    
                except Exception as e:
                    st.error(f"Search failed: {str(e)}")

    # Tips section
    st.markdown("---")
    st.markdown("## 💡 Tips for Better Results")
    st.markdown("""
    - **Use IATA airport codes** (BLR for Bangalore, MUC for Munich)
    - **Be specific**: mention events, airline preferences, connection limits
    - **Natural language works**: "I need direct flights" or "prefer Lufthansa"
    - **LangGraph handles**: Complex routing, connections, and multi-segment flights automatically
    """)

if __name__ == "__main__":
    main()