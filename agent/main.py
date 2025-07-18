import asyncio
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from vocab_processor.agent import graph


async def main():
    # Initialize state
    initial_state: dict[str, str] = {
        "source_word": "Haus",
        "source_language": "German",
        "target_language": "Spanish",
    }

    # Run the graph
    result = await graph.ainvoke(initial_state)

    print(result)

    # async for chunk in graph.astream(initial_state, stream_mode="values"):
    #     print(chunk)


if __name__ == "__main__":
    asyncio.run(main())
