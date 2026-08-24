from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from openai import OpenAI
from openai import AsyncOpenAI
from tools import Get_relevant_webpages, batch_read_pages
from dotenv import load_dotenv
from vector_DB import retrieve_top_k
import os
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")

Smart_model = ChatOpenAI(
    model="openai/gpt-5.6-luna",
    api_key=api_key,
    base_url="https://api.aicredits.in/v1",
)

main_agent_system_prompt = """
You are a research agent.

Your job is to investigate the user's question using the available tools.

Use the provided documents first when relevant. Use web search when additional information is needed.

Do not make up facts. Base your answers on the information you retrieve.

When you have enough information, provide a concise research summary and mention the sources you used.
"""

agent = create_agent(
    model=Smart_model,
    tools=[Get_relevant_webpages, batch_read_pages, retrieve_top_k],
    system_prompt=main_agent_system_prompt
)


async def ask_main_agent(question):
    result = await agent.ainvoke({
        "messages": [
            {"role": "user", "content": question}
        ]
    })

    return result["messages"][-1].content