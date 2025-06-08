"""Centralized prompt templates for LLM interactions."""

def _load_prompt(filename):
    """Load a prompt template from a file."""
    with open(f"asago/prompts/{filename}", "r") as f:
        return f.read()

class PromptTemplates:
    """Collection of prompt templates for different tasks."""

    @staticmethod
    def get_request_parser_prompt(
        departure_city: str,
        arrival_city: str,
        departure_range: tuple,
        return_range: tuple,
    ) -> str:
        """Generate prompt for parsing user travel requests."""

        prompt = _load_prompt("request_parser.txt")
        return prompt.format(
            departure_city=departure_city,
            arrival_city=arrival_city,
            departure_range_start=departure_range[0],
            departure_range_end=departure_range[1],
            return_range_start=return_range[0],
            return_range_end=return_range[1],
        )

    @staticmethod
    def get_results_formatter_prompt() -> str:
        """Generate prompt for formatting flight search results."""

        prompt = _load_prompt("results_formatter.txt")
        return prompt


    @staticmethod
    def get_preference_extraction_prompt(user_query: str) -> str:
        """Extract structured preferences from natural language."""
        
        prompt = _load_prompt("preference_extraction.txt")
        return prompt.format(user_query=user_query)
