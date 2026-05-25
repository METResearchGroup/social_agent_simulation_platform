"""LangChain LLM client for simulation v2 agents."""

from __future__ import annotations

from typing import TypeVar

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from lib.load_env_vars import EnvVarsContainer

DEFAULT_MODEL = "gpt-5-nano"
T = TypeVar("T", bound=BaseModel)


def get_chat_model(*, model: str = DEFAULT_MODEL, temperature: float = 0.7) -> ChatOpenAI:
    """Return a configured ChatOpenAI instance."""
    api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    return ChatOpenAI(model=model, temperature=temperature, api_key=api_key)


def invoke_structured(
    prompt: ChatPromptTemplate,
    output_model: type[T],
    **prompt_variables: object,
) -> T:
    """Invoke the LLM with structured output parsing."""
    llm = get_chat_model()
    structured_llm = llm.with_structured_output(output_model)
    chain = prompt | structured_llm
    result = chain.invoke(prompt_variables)
    if not isinstance(result, output_model):
        raise TypeError(
            f"Expected {output_model.__name__}, got {type(result).__name__}"
        )
    return result
