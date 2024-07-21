import hashlib
import json
import os
import subprocess
from functools import wraps

import anthropic
import backoff
import openai
from dotenv import load_dotenv

load_dotenv(override=True)



# default_system_message = """You are being run in a scaffold in a shell. When you want to run a shell command, write it in a <bash> XML tag. You will be shown the result of the command and be able to run more commands. Other things you say will be sent to the user. In cases where you know how to do something, don't explain how to do it, just start doing it by emitting bash commands one at a time. Avoid interactive commands. Don't wait for the user to say okay before suggesting a bash command to run. If possible, don't include explanation, just say the command."""

default_system_message = """You are a helpful assistant."""
clients = {}

openai_models = ["gpt-3.5-turbo", "gpt-4-turbo-preview"]
oai = openai.OpenAI()
clients.update({model: oai.chat.completions for model in openai_models})


# perplexity API is pretty shitty, takes incredibly long or you get rate limits immediately
try:
    pplx = openai.OpenAI(
        api_key=os.environ["PERPLEXITY"], base_url="https://api.perplexity.ai"
    )
    pplx_models = [
        "pplx-7b-chat",
        "pplx-70b-chat",
        "pplx-7b-online",
        "pplx-70b-online",
        "llama-2-70b-chat",
        "codellama-34b-instruct",
        "codellama-70b-instruct",
        "mistral-7b-instruct",
        "mixtral-8x7b-instruct",
    ]
    clients.update({model: pplx.chat.completions for model in pplx_models})
except:  # noqa
    pplx_models = []
    pplx = None


try:
    together_ai = openai.OpenAI(
        api_key=os.environ.get("TOGETHER_API_KEY"), base_url="https://api.together.xyz"
    )
    together_ai_models = [
        "codellama/CodeLlama-13b-Instruct-hf",
        "codellama/CodeLlama-34b-Instruct-hf",
        "codellama/CodeLlama-70b-Instruct-hf",
        "codellama/CodeLlama-7b-Instruct-hf",
        "mistralai/Mistral-7B-Instruct-v0.2",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
    ]
    clients.update(
        {model: together_ai.chat.completions for model in together_ai_models}
    )
except:  # noqa
    together_ai = None
    together_ai_models = []


try:
    anthr = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
    anthr_models = ["claude-2.1", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
except:  # noqa
    anthr = None
    anthr_models = []


models = openai_models + together_ai_models + anthr_models


def system_message_to_init_history(content):
    return [{"role": "system", "content": content}]


def get_response_oai(model, history, temperature, *, seed=None, **kwargs):
    client = clients[model]
    response = client.create(
        model=model, messages=history, temperature=temperature, seed=seed, **kwargs
    )
    response_msg = {"role": "assistant", "content": response.choices[0].message.content}
    return response_msg


def get_response_anthropic(model, history, temperature, *, max_tokens=1024, **kwargs):
    system_msg = [msg for msg in history if msg["role"] == "system"]
    system_msg = None if len(system_msg) == 0 else system_msg[0]["content"]
    history = [msg for msg in history if not msg["role"] == "system"]
    message = anthr.messages.create(
        model=model,
        messages=history,
        temperature=temperature,
        max_tokens=max_tokens,
        system=system_msg,
        **kwargs,
    )
    response_msg = {"role": "assistant", "content": message.content[0].text}
    return response_msg


@backoff.on_exception(
    wait_gen=backoff.expo,
    exception=(
        openai.RateLimitError,
        openai.APIConnectionError,
        openai.APITimeoutError,
        openai.InternalServerError,
        anthropic.APIConnectionError,
        anthropic.RateLimitError,
        anthropic.APIStatusError,
    ),
    max_value=60,
    factor=1.5,
)
def get_response(model, history, temperature, *, seed=None, **kwargs):
    print("**Sending request**")
    if model.startswith("test"):
        print("test called")
        return {"role": "assistant", "content": "yo"}

    with open(".llm-cache/last-request.json", "w") as f:
        f.write(
            json.dumps(
                {
                    "model": model,
                    "history": history,
                    "temperature": temperature,
                    "seed": seed,
                    "kwargs": kwargs,
                },
                indent=4,
            )
        )

    if model in anthr_models and kwargs.get("max_tokens") is None:
        response_msg = get_response_anthropic(model, history, temperature, **kwargs)
    else:
        response_msg = get_response_oai(
            model, history, temperature, seed=seed, **kwargs
        )

    with open(".llm-cache/last-response.json", "w") as f:
        f.write(
            json.dumps(
                {
                    "response": response_msg,
                    "model": model,
                    "history": history,
                    "temperature": temperature,
                    "seed": seed,
                },
                indent=4,
            )
        )
    return response_msg


class Agent:
    """A simple scaffolded agent that can do bash calls"""

    def __init__(
        self,
        system_message="You are a helpful assistant",
        temperature=1,
        model=models[0],
        print_messages=False,
        has_bash=False,
    ):
        self.history = system_message_to_init_history(system_message)
        self.init_history = list(self.history)
        self.temperature = temperature
        self.model = model
        self.name = f"{model} @ T={temperature}"
        self.print_messages = print_messages
        self.has_bash = has_bash

    def reply(self, msg, *, reset_conversation=True, seed=None):
        """Add the message to the history and let gpt run until no more <bash>command</bash> is in its output"""
        if reset_conversation:
            self.history = list(self.init_history)
        if self.print_messages:
            print(msg)
        self.history.append({"role": "user", "content": msg})
        while True:
            response = get_response(
                model=self.model,
                history=self.history,
                temperature=self.temperature,
                seed=seed,
            )
            if self.print_messages:
                print(response["content"])
            self.history.append(response)
            if self.has_bash and "<bash>" in response["content"]:
                self.execute(response["content"])
            else:
                return response["content"]

    def execute(self, respone_str: str):
        """Execute the command in the response and add the output to the history"""
        cmd = respone_str.split("<bash>")[1].split("</bash>")[0]
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = f"Output: \n{result.stdout}"
        if result.stderr:
            output += f"\nError captured:\n{result.stderr}"
        self.history.append({"role": "user", "content": output})


def get_agents(
    system_messages=["You are a helpful assistant."],
    models=models,
    temperatures=[0, 1],
    agent_kwargs={},
):
    agents = []
    for system_message in system_messages:
        for model in models:
            for t in temperatures:
                agents.append(
                    Agent(
                        system_message=system_message,
                        model=model,
                        temperature=t,
                        **agent_kwargs,
                    )
                )
    return agents


def cli():
    """Chat with an agent - nice for working on the agent"""
    agent = Agent()
    while True:
        msg = input("> ")
        if msg == "q":
            return
        agent.reply(msg)


if __name__ == "__main__":
    cli()