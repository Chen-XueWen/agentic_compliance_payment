from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.config import LLM_MODEL, LLM_BASE_URL

# Initialize LLM
llm = ChatOllama(model=LLM_MODEL, base_url=LLM_BASE_URL, temperature=0)

def get_llm_chain(template: str):
    prompt = ChatPromptTemplate.from_template(template)
    return prompt | llm | StrOutputParser()
