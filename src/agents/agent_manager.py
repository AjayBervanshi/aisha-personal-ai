import logging
from typing import Dict, Any, List

log = logging.getLogger(__name__)

class SpecialistAgent:
    def __init__(self, name: str, description: str, system_prompt: str):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        # In a full implementation, this would hold tools specific to the role.

    def execute(self, task: str, context: Dict[str, Any]) -> str:
        """
        Simulate the execution of a specialized task.
        In the future, this will hook into Aisha's LLM router.
        """
        log.info(f"Sub-agent '{self.name}' executing task: {task[:50]}...")
        # For now, return a mocked response indicating the agent did its job.
        # This will be upgraded to actual LLM calls when integrated with ai_router.py
        return f"[{self.name} output]: Successfully processed '{task}'."

class AgentManager:
    """
    Manages specialist sub-agents that Aisha can delegate tasks to.
    """
    def __init__(self):
        self.agents: Dict[str, SpecialistAgent] = {}
        self._register_default_agents()

    def _register_default_agents(self):
        self.register_agent(SpecialistAgent(
            name="Researcher",
            description="Searches the web and extracts deep factual information.",
            system_prompt="You are an expert researcher. Find and summarize facts."
        ))
        self.register_agent(SpecialistAgent(
            name="Analyst",
            description="Analyzes data, code, or complex logic.",
            system_prompt="You are an expert analyst. Break down complex data."
        ))

    def register_agent(self, agent: SpecialistAgent):
        self.agents[agent.name.lower()] = agent

    def get_available_agents(self) -> List[Dict[str, str]]:
        return [{"name": a.name, "description": a.description} for a in self.agents.values()]

    def delegate(self, agent_name: str, task: str, context: Dict[str, Any]) -> str:
        agent_name = agent_name.lower()
        if agent_name not in self.agents:
            return f"Error: Agent '{agent_name}' not found."

        agent = self.agents[agent_name]
        result = agent.execute(task, context)
        return result

# Global singleton for use across Aisha
agent_manager = AgentManager()
