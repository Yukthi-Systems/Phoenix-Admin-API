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
from src.utils.base.constants import OPENAI_API_KEY, SYSTEM_PROMPT
from src.utils.models import All_Exceptions


def answer_user_query(query: str, context: str, user_name: str) -> str:
    """
    Answer a user query using OpenAI's API
    """
    query = query.strip()
    if not query:
        raise All_Exceptions(message="Query cannot be empty", status_code=status.HTTP_400_BAD_REQUEST)
    
    if len(query) < 30 or len(query) > 250:
        raise All_Exceptions(message="Query must be between 30 and 250 characters", status_code=status.HTTP_400_BAD_REQUEST)

    query = f"Hi, I am '{user_name}'. {query}"

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.responses.create(
            model="gpt-4.1-nano",
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": SYSTEM_PROMPT
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Context: ```{context}```\n\nQuestion: ```{query}```"
                        }
                    ]
                }
            ],
            text={
                "format": {
                    "type": "text"
                }
            },
            metadata={
                "user_name": user_name
            },
            reasoning={},
            tools=[],
            temperature=1,
            max_output_tokens=512,
            top_p=1,
            store=True
        )
        logging.info(f"Answer for query '{query}' usage: {response.usage}")

        return response.output_text

    except Exception as e:
        logging.error(f"Error while answering user query using OpenAI: {e}", exc_info=True)
        raise All_Exceptions(message="Failed to answer user query", status_code=status.HTTP_410_GONE)
