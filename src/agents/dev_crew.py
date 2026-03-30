import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from src.agents.tools.file_tools import read_file, write_file, list_directory, save_to_journal
from src.agents.tools.execution_tools import run_python_tests, check_python_syntax

def get_llm(provider: str, model_name: str = None):
    """Returns the appropriate LangChain LLM based on available API keys."""
    if provider == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and "your_" not in key:
            return ChatGoogleGenerativeAI(model=model_name or "gemini-1.5-pro", google_api_key=key, temperature=0.7)
    elif provider == "groq":
        key = os.getenv("GROQ_API_KEY")
        if key and "your_" not in key:
            return ChatGroq(model_name=model_name or "llama3-70b-8192", groq_api_key=key, temperature=0)
    elif provider == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY")
        if key and "your_" not in key:
            return ChatAnthropic(model_name=model_name or "claude-3-5-sonnet-20241022", api_key=key, temperature=0.7)
    elif provider == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and "your_" not in key:
            return ChatOpenAI(model_name=model_name or "gpt-4o", api_key=key, temperature=0.7)

    # Fallback to whatever is available
    if os.getenv("GEMINI_API_KEY"): return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
    if os.getenv("GROQ_API_KEY"): return ChatGroq(model_name="llama3-8b-8192", groq_api_key=os.getenv("GROQ_API_KEY"))
    return ChatOpenAI(model_name="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

@CrewBase
class DevCrew:
    """DevCrew for Self-Improvement and Bug Fixing."""

    agents_config = 'config/dev_agents.yaml'
    tasks_config = 'config/dev_tasks.yaml'

    @agent
    def architect(self) -> Agent:
        return Agent(
            config=self.agents_config['architect'],
            verbose=True,
            llm=get_llm("anthropic", "claude-3-5-sonnet-20241022"), # Claude for complex planning
            tools=[read_file, list_directory],
        )

    @agent
    def dev(self) -> Agent:
        return Agent(
            config=self.agents_config['dev'],
            verbose=True,
            llm=get_llm("gemini", "gemini-1.5-pro"), # Gemini Pro for best coding
            tools=[read_file, write_file, check_python_syntax],
        )

    @agent
    def tester(self) -> Agent:
        return Agent(
            config=self.agents_config['tester'],
            verbose=True,
            llm=get_llm("groq", "llama3-70b-8192"), # Groq/Llama-3 for fast test writing
            tools=[read_file, write_file, run_python_tests],
        )

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config['reviewer'],
            verbose=True,
            llm=get_llm("groq", "llama3-70b-8192"), # Groq for quick code review
            tools=[read_file, save_to_journal],
        )

    @task
    def architect_task(self) -> Task:
        return Task(config=self.tasks_config['architect_task'])

    @task
    def write_code_task(self) -> Task:
        return Task(config=self.tasks_config['write_code_task'])

    @task
    def test_code_task(self) -> Task:
        return Task(config=self.tasks_config['test_code_task'])

    @task
    def review_code_task(self) -> Task:
        return Task(config=self.tasks_config['review_code_task'])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
