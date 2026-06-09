from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from func.tools import (
    fetch_ecc_data,
    get_pipeline_status,
    map_fields_with_llm,
    preview_data,
    transform_ecc_data,
    write_to_s4hana,
)
from llm.model import map_data_llm

load_dotenv()

_SYSTEM_PROMPT = """You are an SAP migration agent that helps migrate vendor master data
from SAP ECC to S/4HANA Business Partner records.

You have access to these tools that represent each stage of the ETL pipeline:

1. get_pipeline_status  — check which stages have completed and record counts
2. fetch_ecc_data       — extract vendor records from ECC OData API
3. transform_ecc_data   — clean and normalize the raw ECC data
4. map_fields_with_llm  — use AI to map ECC fields to S/4HANA BP fields
5. preview_data         — inspect rows at 'ecc' or 's4' stage
6. write_to_s4hana      — create Business Partner records in S/4HANA

Always run stages in order: fetch → transform → map → write.
After each stage, report the record count and any important details before proceeding.
If the user asks to run the full pipeline, run all four stages in sequence.
"""

tools = [
    get_pipeline_status,
    fetch_ecc_data,
    transform_ecc_data,
    map_fields_with_llm,
    preview_data,
    write_to_s4hana,
]

agent = create_agent(map_data_llm, tools=tools, system_prompt=_SYSTEM_PROMPT)


def run_agent(user_input: str, chat_history: list) -> str:
    messages = []
    for msg in chat_history:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})
    messages.append({"role": "user", "content": user_input})

    result = agent.invoke({"messages": messages})
    return result["messages"][-1].content


if __name__ == "__main__":
    print("=" * 60)
    print("  SAP ECC → S/4HANA Migration Agent")
    print("=" * 60)

    response = run_agent("Run the full migration pipeline", [])
    print(f"\n{response}")
