from vocab_processor.agent import graph
import asyncio

async def main():
    # Initialize state
    initial_state: dict[str, str] = {
        "source_word": "voegeln",
        "target_language": "Spanish"
    }

    # Run the graph
    # result = await graph.ainvoke(initial_state)

    # print(result)

    async for chunk in graph.astream(initial_state, stream_mode="values"):
        print(chunk)
    

if __name__ == "__main__":
    asyncio.run(main())
