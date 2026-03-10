from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

@CrewBase
class YouTubeCrew:
    """YouTubeCrew for Aisha's Video Empire Pipeline."""

    agents_config = 'config/youtube_agents.yaml'
    tasks_config = 'config/youtube_tasks.yaml'

    @agent
    def riya(self) -> Agent:
        return Agent(config=self.agents_config['riya'], verbose=True)

    @agent
    def lexi(self) -> Agent:
        return Agent(config=self.agents_config['lexi'], verbose=True)

    @agent
    def zara(self) -> Agent:
        return Agent(config=self.agents_config['zara'], verbose=True)

    @agent
    def aria(self) -> Agent:
        return Agent(config=self.agents_config['aria'], verbose=True)

    @agent
    def mia(self) -> Agent:
        return Agent(config=self.agents_config['mia'], verbose=True)

    @agent
    def sync(self) -> Agent:
        return Agent(config=self.agents_config['sync'], verbose=True)

    @agent
    def cappy(self) -> Agent:
        return Agent(config=self.agents_config['cappy'], verbose=True)

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
