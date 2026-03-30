from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from src.agents.dev_crew import get_llm
from src.agents.tools.media_tools import generate_audio, generate_image, sync_video
from src.agents.tools.youtube_tools import search_youtube_trends, upload_to_youtube

@CrewBase
class YouTubeCrew:
    """YouTubeCrew for Aisha's Video Empire Pipeline."""

    agents_config = 'config/youtube_agents.yaml'
    tasks_config = 'config/youtube_tasks.yaml'

    @agent
    def riya(self) -> Agent:
        return Agent(
            config=self.agents_config['riya'],
            verbose=True,
            tools=[search_youtube_trends],
            llm=get_llm("gemini", "gemini-1.5-flash") # Great for fast web research
        )

    @agent
    def lexi(self) -> Agent:
        return Agent(
            config=self.agents_config['lexi'],
            verbose=True,
            llm=get_llm("anthropic", "claude-3-haiku-20240307") # Great for creative storytelling
        )

    @agent
    def zara(self) -> Agent:
        return Agent(
            config=self.agents_config['zara'],
            verbose=True,
            llm=get_llm("groq", "llama3-70b-8192") # Fast factual check
        )

    @agent
    def aria(self) -> Agent:
        return Agent(
            config=self.agents_config['aria'],
            verbose=True,
            tools=[generate_audio],
            llm=get_llm("openai", "gpt-4o-mini") # General purpose mapping
        )

    @agent
    def mia(self) -> Agent:
        return Agent(
            config=self.agents_config['mia'],
            verbose=True,
            tools=[generate_image],
            llm=get_llm("openai", "gpt-4o-mini") # General purpose mapping
        )

    @agent
    def sync(self) -> Agent:
        return Agent(
            config=self.agents_config['sync'],
            verbose=True,
            tools=[sync_video],
            llm=get_llm("gemini", "gemini-1.5-flash") # For final orchestration
        )

    @agent
    def cappy(self) -> Agent:
        return Agent(
            config=self.agents_config['cappy'],
            verbose=True,
            tools=[upload_to_youtube],
            llm=get_llm("groq", "llama3-8b-8192") # Lightweight for title gen
        )

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config['research_task'])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
