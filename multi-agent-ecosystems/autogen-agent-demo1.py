# Minimal AutoGen agent example using OpenAI.
# Sends a single message to a chat model and prints the response.
# Requires OPENAI_API_KEY in a .env file.

from dotenv import load_dotenv
import asyncio
import os
from autogen_core.models import UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Load environment variables from .env
load_dotenv()

async def main():
    # Create an OpenAI chat client
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Send a user message and await the model's response
    response = await model_client.create([
        UserMessage(
            content="What is Microsoft AutoGen?",
            source="user"
        )
    ])

    print(response.content)

    # Release the client connection
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
