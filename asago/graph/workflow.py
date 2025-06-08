"""Workflow for flight search using LangGraph."""
from langgraph.graph import END, StateGraph

from asago.graph.nodes import FlightSearchNodes
from asago.models.state import FlightSearchState


class FlightSearchWorkflow:
    """Workflow for flight search using LangGraph"""
    
    def __init__(self):
        """Initialize the flight search workflow"""
        self.nodes = FlightSearchNodes()
        self.graph = self._create_workflow()
    

    def _create_workflow(self) -> StateGraph:
        """Create LangGraph workflow for flight search"""
        
        # Create the graph
        workflow = StateGraph(FlightSearchState)
        
        # Add nodes
        workflow.add_node("parse_request", self.nodes.parse_user_request_node)
        workflow.add_node("search_flights", self.nodes.search_flights_node)
        workflow.add_node("format_results", self.nodes.format_results_node)

        # Add edges
        workflow.set_entry_point("parse_request")
        workflow.add_edge("parse_request", "search_flights")
        workflow.add_edge("search_flights", "format_results")
        workflow.add_edge("format_results", END)
        
        return workflow.compile()