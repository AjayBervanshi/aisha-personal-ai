from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

@CrewBase
class DevCrew:
    """DevCrew for Self-Improvement and Skill Creation."""

    agents_config = 'config/dev_agents.yaml'
    tasks_config = 'config/dev_tasks.yaml'

    @agent
    def dev(self) -> Agent:
        return Agent(
            config=self.agents_config['dev'],
            verbose=True,
            allow_delegation=False
        )

    @agent
    def tester(self) -> Agent:
        return Agent(
            config=self.agents_config['tester'],
            verbose=True,
            allow_delegation=False
        )

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config['reviewer'],
            verbose=True,
            allow_delegation=False
        )

    @task
    def write_code_task(self) -> Task:
        return Task(
            config=self.tasks_config['write_code_task'],
        )

    @task
    def test_code_task(self) -> Task:
        return Task(
            config=self.tasks_config['test_code_task'],
        )

    @task
    def review_code_task(self) -> Task:
        return Task(
            config=self.tasks_config['review_code_task'],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
