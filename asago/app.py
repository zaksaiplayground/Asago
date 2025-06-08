"""Streamlit app for flight search using LangGraph and Amadeus API."""
import os
from datetime import datetime, timedelta

import streamlit as st

from asago.config import settings
from asago.graph.workflow import FlightSearchWorkflow
from asago.models.state import FlightSearchState

st.set_page_config(
    page_title=settings.page_title, page_icon=settings.page_icon, layout=settings.layout
)

st.title(settings.page_header)


def main():
    """Run the Streamlit app."""
    workflow = FlightSearchWorkflow()
    if "flight_graph" not in st.session_state:
        st.session_state.flight_graph = workflow.graph

    col1, col2 = st.columns([2, 1])

    with col1:

        col1_1, col1_2 = st.columns(2)

        with col1_1:
            departure_city = st.text_input(
                "Departure City (Airport Code)", placeholder="e.g., BLR, NYC"
            )

        with col1_2:
            arrival_city = st.text_input(
                "Arrival City (Airport Code)", placeholder="e.g., MUC, PAR"
            )

        # Date ranges
        col2_1, col2_2 = st.columns(2)

        with col2_1:
            st.subheader("Departure Date Range")
            departure_start = st.date_input(
                "Earliest Departure", datetime.now() + timedelta(days=7)
            )
            departure_end = st.date_input(
                "Latest Departure", datetime.now() + timedelta(days=30)
            )

        with col2_2:
            st.subheader("Return Date Range")
            return_start = st.date_input(
                "Earliest Return", datetime.now() + timedelta(days=14)
            )
            return_end = st.date_input(
                "Latest Return", datetime.now() + timedelta(days=37)
            )

        # Number of passengers
        adults = st.number_input(
            "Number of Adult Passengers", min_value=1, max_value=9, value=1
        )

        # User request
        user_request = st.text_area(
            "Describe your travel preferences or requirements:",
            placeholder="e.g., I want to attend Oktoberfest in Munich, /"
            "need direct flights only, prefer Lufthansa",
            height=100,
        )

    with col2:
        st.header("Search Assistant")

        if st.button("🔍 Search Flights", type="primary"):
            if not departure_city or not arrival_city:
                st.error("Please enter both departure and arrival cities")
                return

            if not all(
                [
                    os.getenv("OPENAI_API_KEY"),
                    os.getenv("AMADEUS_API_KEY"),
                    os.getenv("AMADEUS_API_SECRET"),
                ]
            ):
                st.error("Please ensure all API keys are set in environment variables")
                return

            # Create initial state
            initial_state = FlightSearchState(
                user_query=user_request
                or f"Find flights from {departure_city} to {arrival_city}",
                departure_city=departure_city,
                arrival_city=arrival_city,
                departure_date_range=(departure_start, departure_end),
                return_date_range=(return_start, return_end),
                adults=adults,
                parsed_request={},
                flight_results=[],
                formatted_results="",
                error="",
            )

            # Execute the graph
            with st.spinner("Searching for flights..."):
                try:
                    final_state = st.session_state.flight_graph.invoke(initial_state)

                    if final_state.get("error"):
                        st.error(final_state["error"])
                    else:
                        # Show parsed request info
                        if final_state.get("parsed_request"):
                            st.success("✅ Request analyzed successfully!")
                            parsed = final_state["parsed_request"]
                            if "optimal_departure_date" in parsed:
                                st.info(
                                    "**Suggested dates:** "
                                    f"{parsed['optimal_departure_date']}"
                                    f" to {parsed['optimal_return_date']}"
                                )
                            if "reasoning" in parsed:
                                st.info(f"**Reasoning:** {parsed['reasoning']}")

                        # Show flight results
                        if final_state.get("formatted_results"):
                            st.success("✅ Flights found!")
                            st.markdown("## Flight Options")
                            st.markdown(final_state["formatted_results"])
                        else:
                            st.warning("No flights found for the specified criteria.")

                except Exception as e:
                    st.error(f"Search failed: {str(e)}")

    # Tips section
    st.markdown("---")
    st.markdown("## 💡 Tips for Better Results")
    st.markdown(
        """
    - **Use IATA airport codes** (BLR for Bangalore, MUC for Munich)
    - **Be specific**: mention events, airline preferences, connection limits
    - **Natural language works**: "I need direct flights" or "prefer Lufthansa"
    """
    )


if __name__ == "__main__":
    main()
