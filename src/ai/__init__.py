"""
All the Database related functions are defined here
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


from .deep_infra import (
    answer_user_query as deep_infra_answer_user_query,
    stream_user_query as deep_infra_stream_user_query,
    generate_styling_by_text as deep_infra_generate_styling_by_text
)
from .open_ai import answer_user_query as open_ai_answer_user_query


__version__ = "v1.0.1-phoenix-release"


__annotations__ = {
    "version": __version__,
    "deep_infra_answer_user_query": "A function to answer user queries using DeepInfra's OpenAI API",
    "open_ai_answer_user_query": "A function to answer user queries using OpenAI's API",
    "deep_infra_stream_user_query": "A function to stream answers for user queries using DeepInfra's OpenAI API",
    "deep_infra_generate_styling_by_text": "A function to generate styling suggestions based on text using DeepInfra's OpenAI API"
}


__all__ = [
    "deep_infra_answer_user_query",
    "open_ai_answer_user_query",
    "deep_infra_stream_user_query",
    "deep_infra_generate_styling_by_text"
]
