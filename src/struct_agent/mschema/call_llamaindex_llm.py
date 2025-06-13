import time
from llama_index.core.llms import LLM, ChatMessage
from llama_index.core.prompts import BasePromptTemplate
from typing import Optional, Sequence


def call_llm(prompt: BasePromptTemplate, llm: Optional[LLM] = None, max_try=5, sleep=10, **prompt_args)->str:
    for try_idx in range(max_try):
        try:
            res = llm.predict(prompt, **prompt_args)
            return res
        except Exception as e:  # noqa: F841
            time.sleep(sleep)
    return ''


def call_llm_message(messages: Sequence[ChatMessage], llm: Optional[LLM] = None, max_try=5, sleep=10, **kwargs)->str:
    for try_idx in range(max_try):
        try:
            res = llm.chat(messages, **kwargs)
            return res.message.content
        except Exception as e:  # noqa: F841
            time.sleep(sleep)
    return ''

