from google.genai import types
from google.genai.chats import Chat

from umb_assistant.agent.tools import get_course_prerequisites, get_course_schedule, search_course_catalog
from umb_assistant.agent.prompts import SYSTEM_PROMPT
from umb_assistant.core.config import client as CLIENT

TOOL_MAP = {
    "get_course_prerequisites": get_course_prerequisites,
    "get_course_schedule": get_course_schedule,
    "search_course_catalog": search_course_catalog,
}

class AdvisingAgent:
    def __init__(self,client=None):
        self.model = "gemini-3.5-flash"
        self.client = client or CLIENT
        self.system_prompt = SYSTEM_PROMPT
        self.chat = self._create_new_chat()

    
    def _create_new_chat(self) -> Chat:
        config = {
                "system_instruction": self.system_prompt,
                "tools": list(TOOL_MAP.values()),
                "temperature": 0.2,
                "thinking_config":{
                    "include_thoughts":False
                },
                "max_output_tokens": 2500

            }
        
        chat = self.client.chats.create(
                model=self.model,
                config=types.GenerateContentConfig(**config),
            )
    
        return chat
    
    def send_message(self, query:str) -> str:
        response = self.chat.send_message(f"<student_query>\n{query.strip()}\n</student_query>")
        return response.text


