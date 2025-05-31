import streamlit as st
import os
import json
import asyncio
from dotenv import load_dotenv
from openai import OpenAI
from asago.flight_assistant import EnhancedFlightAssistant
from datetime import datetime, timedelta

# Load API keys and setup
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="🛫 Flight Search Assistant")
st.title("🛫 Flight Search Assistant")
st.markdown("Enter your flight preferences below:")

# GPT Parsing Function
def parse_extra_info(text):
    prompt = f"""
You are a flight assistant. Parse the user's extra flight preferences from free text.
Return JSON with these fields only if they are mentioned:
- preferred_departure_times: ["morning", "afternoon", "evening"]
- max_price: number
- excluded_airlines: list of IATA codes
- flexible_dates: true/false
- sort_by: "price", "duration", "stops", etc.

Text: "{text}"
Return only a JSON object.
"""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
            ],
            temperature=0.2
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Failed to parse extra preferences: {e}")
        return {}

# Main App
def main():
    # Initialize session state for form persistence
    if 'trip_type' not in st.session_state:
        st.session_state.trip_type = "one-way"
    if 'dep_date_option' not in st.session_state:
        st.session_state.dep_date_option = "Single Date"
    if 'ret_date_option' not in st.session_state:
        st.session_state.ret_date_option = "Single Date"

    # Travelers
    col1, col2, col3 = st.columns(3)
    adults = col1.number_input("Adults", min_value=0, max_value=9, value=1)
    children = col2.number_input("Children", min_value=0, max_value=9, value=0)
    infants = col3.number_input("Infants", min_value=0, max_value=9, value=0)

    # Origin and Destination
    origin = st.text_input("Origin Airport Code (e.g., JFK)", max_chars=3)
    destination = st.text_input("Destination Airport Code (e.g., LHR)", max_chars=3)

    # Trip type - using session state for persistence
    trip_type = st.radio(
        "Trip Type", 
        ["one-way", "round-trip"],
        key="trip_type_radio",
        index=0 if st.session_state.trip_type == "one-way" else 1
    )
    st.session_state.trip_type = trip_type
    
    # Departure Date Section
    st.subheader("📅 Departure Date")
    dep_date_option = st.radio(
        "How would you like to specify departure date?",
        ["Single Date", "Date Range"],
        key="dep_date_option_radio"
    )
    st.session_state.dep_date_option = dep_date_option
    
    departure_date = None
    dep_start, dep_end = None, None
    
    if dep_date_option == "Single Date":
        departure_date = st.date_input("Departure Date", key="dep_single_date")
    else:
        st.info("💡 Select your departure date range using the calendars below:")
        col1, col2 = st.columns(2)
        with col1:
            dep_start = st.date_input("Departure Range Start", key="dep_range_start")
        with col2:
            dep_end = st.date_input("Departure Range End", key="dep_range_end")

    # Return Date Section (only for round-trip)
    return_date = None
    ret_start, ret_end = None, None
    
    if trip_type == "round-trip":
        st.subheader("🔄 Return Date")
        ret_date_option = st.radio(
            "How would you like to specify return date?",
            ["Single Date", "Date Range"],
            key="ret_date_option_radio"
        )
        st.session_state.ret_date_option = ret_date_option
        
        if ret_date_option == "Single Date":
            return_date = st.date_input("Return Date", key="ret_single_date")
        else:
            st.info("💡 Select your return date range using the calendars below:")
            col1, col2 = st.columns(2)
            with col1:
                ret_start = st.date_input("Return Range Start", key="ret_range_start")
            with col2:
                ret_end = st.date_input("Return Range End", key="ret_range_end")

    # Flight Preferences
    st.subheader("✈️ Flight Preferences")
    col1, col2 = st.columns(2)
    
    with col1:
        travel_class = st.selectbox("Cabin Class", ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"])
        max_stops = st.selectbox("Maximum Stops", [0, 1, 2])
        currency_code = st.text_input("Currency Code (e.g., USD, EUR)", value="EUR", max_chars=3)
    
    with col2:
        preferred_carriers = st.text_input("Preferred Carriers (comma-separated airline codes, optional)")
        max_price = st.number_input("Maximum Price (optional)", min_value=0, value=0, step=100)
        sort_by = st.selectbox("Sort Results By", ["price", "duration", "stops", "convenience"])

    # Extra preferences
    extra_text = st.text_area(
        "✍️ Additional Preferences", 
        placeholder="e.g., 'prefer morning departures', 'no budget airlines', 'Emirates preferred'",
        height=100
    )

    # Search button outside of form for better reactivity
    if st.button("🔍 Search Flights", type="primary"):
        # Validation
        errors = []
        
        if not origin or len(origin) != 3:
            errors.append("Please enter a valid 3-letter origin airport code")
        if not destination or len(destination) != 3:
            errors.append("Please enter a valid 3-letter destination airport code")
            
        # Departure date validation
        if dep_date_option == "Single Date":
            if not departure_date:
                errors.append("Please select a departure date")
        else:
            if not dep_start or not dep_end:
                errors.append("Please select both departure range start and end dates")
            elif dep_start > dep_end:
                errors.append("Departure range start date must be before end date")
                
        # Return date validation for round-trip
        if trip_type == "round-trip":
            if ret_date_option == "Single Date":
                if not return_date:
                    errors.append("Please select a return date")
                elif departure_date and return_date <= departure_date:
                    errors.append("Return date must be after departure date")
            else:
                if not ret_start or not ret_end:
                    errors.append("Please select both return range start and end dates")
                elif ret_start > ret_end:
                    errors.append("Return range start date must be before end date")
                # Additional validation for return range vs departure
                elif departure_date and ret_start <= departure_date:
                    errors.append("Return range start must be after departure date")
                elif dep_end and ret_start <= dep_end:
                    errors.append("Return range start should be after departure range end")

        if errors:
            for error in errors:
                st.error(error)
            return

        # Parse extra preferences
        extra_preferences = parse_extra_info(extra_text) if extra_text.strip() else {}
        
        # Add max_price to extra preferences if specified
        if max_price > 0:
            extra_preferences["max_price"] = max_price
            
        # Add sort preference
        extra_preferences["sort_by"] = sort_by

        # Build form data
        form_data = {
            "origin": origin.upper(),
            "destination": destination.upper(),
            "trip_type": trip_type,
            "travel_class": travel_class,
            "adults": adults,
            "children": children,
            "infants": infants,
            "preferred_airlines": [code.strip().upper() for code in preferred_carriers.split(",") if code.strip()] if preferred_carriers else [],
            "max_stops": max_stops,
            "currency_code": currency_code.upper(),
            "departure_date": departure_date.strftime("%Y-%m-%d") if departure_date else None,
            "departure_date_range": {
                "start": dep_start.strftime("%Y-%m-%d") if dep_start else None,
                "end": dep_end.strftime("%Y-%m-%d") if dep_end else None,
            } if dep_start and dep_end else None,
            "return_date": return_date.strftime("%Y-%m-%d") if return_date else None,
            "return_date_range": {
                "start": ret_start.strftime("%Y-%m-%d") if ret_start else None,
                "end": ret_end.strftime("%Y-%m-%d") if ret_end else None,
            } if ret_start and ret_end else None,
            "extra_preferences": extra_preferences
        }

        # Display search summary
        st.subheader("🧾 Search Summary")
        
        # Create a more readable summary
        summary_cols = st.columns(2)
        
        with summary_cols[0]:
            st.markdown(f"""
            **✈️ Route:** {form_data['origin']} → {form_data['destination']}
            **👥 Passengers:** {adults} adult(s), {children} child(ren), {infants} infant(s)
            **🎫 Class:** {travel_class}
            **🛑 Max Stops:** {max_stops}
            """)
            
        with summary_cols[1]:
            # Format dates nicely
            if departure_date:
                dep_text = departure_date.strftime("%B %d, %Y")
            elif dep_start and dep_end:
                dep_text = f"{dep_start.strftime('%b %d')} - {dep_end.strftime('%b %d, %Y')}"
            else:
                dep_text = "Not specified"
                
            if return_date:
                ret_text = return_date.strftime("%B %d, %Y")
            elif ret_start and ret_end:
                ret_text = f"{ret_start.strftime('%b %d')} - {ret_end.strftime('%b %d, %Y')}"
            else:
                ret_text = "One-way trip"
                
            st.markdown(f"""
            **📅 Departure:** {dep_text}
            **🔄 Return:** {ret_text}
            **💰 Currency:** {currency_code}
            **📊 Sort By:** {sort_by.title()}
            """)

        # Show raw JSON for debugging (collapsible)
        with st.expander("🔧 Raw Search Data (for debugging)"):
            st.json(form_data)

        # Run the flight search
        with st.spinner("🔍 Searching for flights..."):
            try:
                result = asyncio.run(run_assistant(form_data))
                st.success("✅ Search completed!")
                
                # Display results
                st.subheader("✈️ Flight Search Results")
                st.markdown(result)
                
            except Exception as e:
                st.error(f"❌ Search failed: {str(e)}")
                st.info("Please check your API keys and network connection.")

# Async entrypoint
async def run_assistant(form_data):
    """Run the flight assistant with the form data"""
    assistant = EnhancedFlightAssistant()
    await assistant.initialize_mcp_servers()
    result = await assistant.process_request_enhanced(structured_input=form_data)
    return result

# Add sidebar with tips
with st.sidebar:
    st.markdown("### 💡 Tips")
    st.markdown("""
    **Airport Codes:**
    - Use 3-letter IATA codes (JFK, LHR, CDG)
    - [Look up codes here](https://www.iata.org/en/publications/directories/code-search/)
    
    **Date Ranges:**
    - Use for flexible travel dates
    - Assistant will search multiple date combinations
    - Larger ranges may take longer to search
    
    **Airline Codes:**
    - Use 2-letter IATA codes (BA, LH, EK)
    - Separate multiple airlines with commas
    
    **Extra Preferences:**
    - Natural language is supported
    - Examples: "morning flights", "no layovers", "under $1000"
    """)
    
    st.markdown("### 🔧 Debug")
    if st.button("Test Connection"):
        try:
            if os.getenv("OPENAI_API_KEY"):
                st.success("✅ OpenAI API key found")
            else:
                st.error("❌ OpenAI API key missing")
                
            if os.getenv("AMADEUS_API_KEY"):
                st.success("✅ Amadeus API key found")  
            else:
                st.error("❌ Amadeus API key missing")
        except Exception as e:
            st.error(f"Error checking configuration: {e}")

if __name__ == "__main__":
    main()