import os
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

AICORE_AUTH_URL = os.getenv("AICORE_AUTH_URL")
AICORE_CLIENT_ID = os.getenv("AICORE_CLIENT_ID")
AICORE_CLIENT_SECRET = os.getenv("AICORE_CLIENT_SECRET")
AICORE_RESOURCE_GROUP = os.getenv("AICORE_RESOURCE_GROUP")
AICORE_BASE_URL = os.getenv("AICORE_BASE_URL")
LLM_DEPLOYMENT_ID = os.getenv("LLM_DEPLOYMENT_ID")

def get_llm(temperature=0):
    return ChatOpenAI(
        deployment_id=LLM_DEPLOYMENT_ID,
        temperature=temperature
    )
