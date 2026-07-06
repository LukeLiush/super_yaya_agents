import asyncio

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client


async def main():
    async with streamablehttp_client("http://127.0.0.1:8288/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result: types.CallToolResult = await session.call_tool("list_functions", {})
            print(result.content)


asyncio.run(main())
