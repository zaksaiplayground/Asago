from typing import Any, Dict, List
from mcp.server import Server
from mcp.types import Tool, TextContent
from duckduckgo_search import DDGS
import json


class WebSearchServer:
    def __init__(self):
        self.server = Server("websearch")
        self.ddgs = DDGS()
        self.setup_tools()

    def setup_tools(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="web_search",
                    description="Search the web using DuckDuckGo",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "max_results": {"type": "integer", "description": "Maximum results", "default": 5},
                            "region": {"type": "string", "description": "Search region", "default": "us-en"}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="news_search",
                    description="Search for news using DuckDuckGo",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "News search query"},
                            "max_results": {"type": "integer", "description": "Maximum results", "default": 5}
                        },
                        "required": ["query"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            if name == "web_search":
                return await self.web_search(**arguments)
            elif name == "news_search":
                return await self.news_search(**arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def web_search(self, query: str, max_results: int = 5, region: str = "us-en") -> List[TextContent]:
        try:
            results = list(self.ddgs.text(query, max_results=max_results, region=region))
            
            search_results = []
            for result in results:
                search_results.append({
                    'title': result.get('title', ''),
                    'url': result.get('href', ''),
                    'snippet': result.get('body', '')
                })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    'status': 'success',
                    'query': query,
                    'results': search_results
                }, indent=2)
            )]
            
        except Exception as error:
            return [TextContent(
                type="text",
                text=json.dumps({
                    'status': 'error',
                    'message': str(error)
                })
            )]

    async def news_search(self, query: str, max_results: int = 5) -> List[TextContent]:
        try:
            results = list(self.ddgs.news(query, max_results=max_results))
            
            news_results = []
            for result in results:
                news_results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'snippet': result.get('body', ''),
                    'date': result.get('date', ''),
                    'source': result.get('source', '')
                })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    'status': 'success',
                    'query': query,
                    'results': news_results
                }, indent=2)
            )]
            
        except Exception as error:
            return [TextContent(
                type="text",
                text=json.dumps({
                    'status': 'error',
                    'message': str(error)
                })
            )]