from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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

prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

agent = create_openai_tools_agent(map_data_llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


def run_agent(user_input: str, chat_history: list) -> str:
    result = agent_executor.invoke({
        "input": user_input,
        "chat_history": chat_history,
    })
    return result["output"]


if __name__ == "__main__":
    print("=" * 60)
    print("  SAP ECC → S/4HANA Migration Agent")
    print("  Type 'exit' to quit.")
    print("=" * 60)

    chat_history = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye.")
            break

        if not user_input:
            continue

        response = run_agent(user_input, chat_history)
        print(f"\nAgent: {response}")

        chat_history.extend([
            HumanMessage(content=user_input),
            AIMessage(content=response),
        ])
