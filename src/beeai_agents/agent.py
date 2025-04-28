from pydantic_settings import BaseSettings

import asyncio
import sys
import traceback

import requests
import base64
import os
from typing import Any
from dotenv import load_dotenv

from beeai_framework.agents.react import ReActAgent
from beeai_framework.emitter import EventMeta
from beeai_framework.errors import FrameworkError
from beeai_framework.memory import TokenMemory
from beeai_framework.backend import ChatModel
from beeai_framework.tools.tool import Tool
from beeai_framework.tools.types import ToolRunOptions, StringToolOutput
from pydantic import BaseModel, Field
from beeai_framework.emitter.emitter import Emitter
from beeai_framework.context import RunContext
from beeai_framework.agents import AgentExecutionConfig

load_dotenv()

GITHUB_API_URL= os.environ.get("GITHUB_API_URL")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

PROD_FLAG = (os.getenv('PROD_FLAG', 'False') == 'True')

git_headers = {
    'Authorization': f'token {ACCESS_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}



class MendScanReportToolInput(BaseModel):
    git_repo_org_owner:str = Field(description= "Owner or Ogranisation name to whom this git repo belongs to")
    git_repo_name:str = Field(description= "Name of the github repository")
    pr_id:str = Field(description= "The id of the pull request")


class GetRequirementsTool(Tool[MendScanReportToolInput, ToolRunOptions, StringToolOutput]):
    name = "get_requirements_file"
    description = "Fetches the requirements.txt file from the latest commit of a given PR, return None if file not found"
    input_schema = MendScanReportToolInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "github", "requirement_file"],
            creator=self,
        )

    async def _run(
        self, input: MendScanReportToolInput, options: ToolRunOptions | None, context: RunContext
    ) -> StringToolOutput:
        # Get PR details to find the latest commit
        pr_url = f"{GITHUB_API_URL}/repos/{input.git_repo_org_owner}/{input.git_repo_name}/pulls/{input.pr_id}"
        pr_response = requests.get(pr_url, headers=git_headers).json()
        commit_sha = pr_response.get("head", {}).get("sha")
        print("commit_sha= ",commit_sha)

        # Get the requirements.txt file content
        file_url = f"{GITHUB_API_URL}/repos/{input.git_repo_org_owner}/{input.git_repo_name}/contents/requirements.txt?ref={commit_sha}"
        file_response = requests.get(file_url, headers=git_headers).json()

        if "content" in file_response:
            print(base64.b64decode(file_response["content"]).decode("utf-8"))
            return StringToolOutput(base64.b64decode(file_response["content"]).decode("utf-8"))
        
        return None
    

async def github_requirements_agent() -> ReActAgent:
    """Create and configure the agent with tools and LLM"""

    llm = ChatModel.from_name(
        "watsonx:meta-llama/llama-3-405b-instruct",
    options={
        "project_id": os.environ["WATSONX_PROJECT_ID"],
        "api_key": os.environ["WATSONX_API_KEY"],
        "api_base": os.environ["WATSONX_API_URL"],
    },
)

    # Create agent with memory and tools and custom system prompt template
    agent = ReActAgent(
        llm=llm,
        tools=[GetRequirementsTool()],
        memory=TokenMemory(llm),
        templates={
            "system": lambda template: template.update(
                defaults={
                    "instructions": """
                        You are a helpful assistant. When asked a question you have to smartly get the correct answer.
                    """
                }
            )
        },
    )
    return agent


def print_events(data: Any, event: EventMeta) -> None:
    """Print agent events"""
    if event.name in ["start", "retry", "update", "success", "error"]:
        print(f"\n** Event ({event.name}): {event.path} **\n{data}")


