"""
boss_aisha.py
=============
Aisha acts as the Manager of the CrewAI multi-agent system.
When she gets a complex request (like coding or YouTube generation),
she spins up the appropriate Crew to handle it.
"""

import logging

log = logging.getLogger("Aisha.Boss")


class AishaManager:
    def __init__(self):
        pass

    def delegate_task(
        self, task_description: str, task_type: str = "coding"
    ) -> str:
        """
        Spins up the right crew based on the task type.
        task_type can be 'coding', 'youtube', etc.
        """
        log.info(
            f"Aisha Boss is delegating a {task_type} task: {task_description}"
        )

        if task_type == "coding":
            from src.agents.dev_crew import DevCrew
            crew = DevCrew().crew()
            result = crew.kickoff(
                inputs={'task_description': task_description}
            )
            return str(result)

        elif task_type == "youtube":
            from src.agents.youtube_crew import YouTubeCrew
            crew = YouTubeCrew().crew()
            result = crew.kickoff(inputs={'topic': task_description})
            return str(result)

        return "I don't have a team for that yet!"
