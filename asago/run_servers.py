import asyncio
import sys
from mcp.server.stdio import stdio_server

async def run_amadeus_server():
    """Run the Amadeus MCP server"""
    print("[SERVER] Starting Amadeus MCP server...", flush=True)
    from amadeus_server import AmadeusServer
    server_instance = AmadeusServer()

    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream, 
            write_stream, 
            server_instance.server.create_initialization_options()
        )

async def run_websearch_server():
    """Run the WebSearch MCP server"""
    from websearch_server import WebSearchServer
    server_instance = WebSearchServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream, 
            write_stream, 
            server_instance.server.create_initialization_options()
        )

if __name__ == "__main__":
    print(sys.argv)
    if len(sys.argv) < 2:
        print("Usage: python run_servers.py [amadeus|websearch]")
        sys.exit(1)
    
    server_type = sys.argv[1]

    if server_type == "amadeus":
        asyncio.run(run_amadeus_server())
    elif server_type == "websearch":
        asyncio.run(run_websearch_server())
    else:
        print("Unknown server type. Use 'amadeus' or 'websearch'")