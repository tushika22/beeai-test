from acp.server.highlevel import Context
from beeai_sdk.providers.agent import Server
from beeai_sdk.schemas.text import TextInput, TextOutput
from agent import github_agent, print_events
from beeai_framework.agents import AgentExecutionConfig

from beeai_agents.configuration import Configuration

server = Server("beeai-agents")

@server.agent()
async def github_requirements_agent(input: TextInput, ctx: Context) -> TextOutput:
    agent = await github_agent()

    response = await agent.run(
        prompt="Give me requirements file for repo org name = b2b-enterprise-services , repo name = s4_hana_backend, pr id = 120",
        execution=AgentExecutionConfig(max_retries_per_step=3, total_max_retries=10, max_iterations=20),
     ).on("*", print_events)
    
    return TextOutput(response.result.text)

    # print("Agent 🤖 : ", response.result.text)
    # return TextOutput(text=Configuration().hello_template % input.text)