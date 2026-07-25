"""
DeepInfra OpenAI related functions are implemented here
"""

"""
Copyright (C) 2026 Yukthi Systems Private Limited

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3
as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
version 3 along with this program. If not, see
<https://www.gnu.org/licenses/>.
"""


from src.utils.base.libraries import OpenAI, logging, status
from src.utils.base.constants import DEEP_INFRA_API_KEY, DEEP_INFRA_API_URL, SYSTEM_PROMPT, SYSTEM_PROMPT_FOR_STYLING
from src.utils.models import All_Exceptions


def answer_user_query(query: str, context: str, user_name: str) -> str:
    """
    Answers the user query using the OpenAI API
    """
    query = query.strip()
    if not query:
        raise All_Exceptions(message="Query cannot be empty", status_code=status.HTTP_400_BAD_REQUEST)
    
    if len(query) < 30 or len(query) > 250:
        raise All_Exceptions(message="Query must be between 30 and 250 characters", status_code=status.HTTP_400_BAD_REQUEST)

    query = f"Hi, I am '{user_name}'. {query}"

    try:
        client = OpenAI(api_key=DEEP_INFRA_API_KEY, base_url=DEEP_INFRA_API_URL)
        response = client.chat.completions.create(
            # model="meta-llama/Meta-Llama-3.1-8B-Instruct",    # Good: $.05
            # model="openai/gpt-oss-20b", # Very very good: $.16 - Very high token consumption
            # model="mistralai/Mistral-Small-3.2-24B-Instruct-2506",  # Good: $.1
            # model="meta-llama/Llama-3.3-70B-Instruct-Turbo",    # Bad: $.12
            # model="Qwen/Qwen2.5-7B-Instruct",   # Good: $.1
            model="Sao10K/L3-8B-Lunaris-v1-Turbo",  # Very good: $.05
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context: ```{context}```\n\nQuestion: ```{query}```"}
            ]
        )
        answer = response.choices[0].message.content.strip()
        logging.info(f"Answer for query '{query}' took {response.usage.prompt_tokens} prompt tokens and {response.usage.completion_tokens} completion tokens.")
        return answer

    except Exception as e:
        logging.error(f"Error while answering user query using DeepInfra: {e}", exc_info=True)
        raise All_Exceptions(message="Failed to answer user query", status_code=status.HTTP_410_GONE)


def stream_user_query(query: str, context: str, user_name: str):
    """
    Streams the answer for the user query using the OpenAI API
    """
    query = query.strip()
    if not query:
        raise All_Exceptions(message="Query cannot be empty", status_code=status.HTTP_400_BAD_REQUEST)
    
    if len(query) < 30 or len(query) > 250:
        raise All_Exceptions(message="Query must be between 30 and 250 characters", status_code=status.HTTP_400_BAD_REQUEST)

    query = f"Hi, I am '{user_name}'. {query}"


    client = OpenAI(api_key=DEEP_INFRA_API_KEY, base_url=DEEP_INFRA_API_URL)
    response_stream = client.chat.completions.create(
        # model="meta-llama/Meta-Llama-3.1-8B-Instruct",    # Good: $.05
        # model="openai/gpt-oss-20b", # Very very good: $.16 - Very high token consumption
        # model="mistralai/Mistral-Small-3.2-24B-Instruct-2506",  # Good: $.1
        # model="meta-llama/Llama-3.3-70B-Instruct-Turbo",    # Bad: $.12
        # model="Qwen/Qwen2.5-7B-Instruct",   # Good: $.1
        model="Sao10K/L3-8B-Lunaris-v1-Turbo",  # Very good: $.05
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context: ```{context}```\n\nQuestion: ```{query}```"}
        ],
        stream=True
    )

    # Generator that yields streamed chunks
    for event in response_stream:
        if event.choices[0].finish_reason:
            logging.info(
                f"Streaming finished: {event.choices[0].finish_reason}, "
                f"{event.usage['prompt_tokens']} prompt tokens, "
                f"{event.usage['completion_tokens']} completion tokens."
            )
            break
        else:
            delta = event.choices[0].delta.content
            if delta:
                yield delta  # stream partial content


def generate_styling_by_text(query: str) -> str:
    """
    Answers the user query using the OpenAI API
    """
    query = query.strip()
    if not query:
        raise All_Exceptions(message="Query cannot be empty", status_code=status.HTTP_400_BAD_REQUEST)

    if len(query) < 100 or len(query) > 500:
        raise All_Exceptions(message="Query must be between 100 and 500 characters", status_code=status.HTTP_400_BAD_REQUEST)

    try:
        client = OpenAI(api_key=DEEP_INFRA_API_KEY, base_url=DEEP_INFRA_API_URL)
        response = client.chat.completions.create(
            # model="meta-llama/Meta-Llama-3.1-8B-Instruct",    # Good: $.05
            # model="openai/gpt-oss-20b", # Very very good: $.16 - Very high token consumption
            # model="mistralai/Mistral-Small-3.2-24B-Instruct-2506",  # Good: $.1
            # model="meta-llama/Llama-3.3-70B-Instruct-Turbo",    # Bad: $.12
            # model="Qwen/Qwen2.5-7B-Instruct",   # Good: $.1
            model="Sao10K/L3-8B-Lunaris-v1-Turbo",  # Very good: $.05
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_FOR_STYLING},
                {"role": "user", "content": query}
            ]
        )
        answer = response.choices[0].message.content.strip()
        logging.info(f"Answer for query '{query}' took {response.usage.prompt_tokens} prompt tokens and {response.usage.completion_tokens} completion tokens.")
        return answer

    except Exception as e:
        logging.error(f"Error while answering user query using DeepInfra: {e}", exc_info=True)
        raise All_Exceptions(message="Failed to answer user query", status_code=status.HTTP_410_GONE)
