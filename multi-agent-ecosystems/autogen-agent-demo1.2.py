# Minimal AutoGen agent example using OpenAI.
# Sends a user-provided message to a chat model and prints the response.
# Requires OPENAI_API_KEY in a .env file.

from dotenv import load_dotenv
import asyncio
import os
from autogen_core.models import UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

load_dotenv()

async def main():
    query = input("Enter your query: ").strip()
    if not query:
        print("No query entered. Exiting.")
        return

    model_client = OpenAIChatCompletionClient(
        model="gpt-5-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    response = await model_client.create([
        UserMessage(content=query, source="user")
    ])

    print(response.content)

    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
