import re
import logging
from typing import Dict, Any, List

log = logging.getLogger(__name__)

class SpecialistAgent:
    def __init__(self, name: str, description: str, system_prompt: str):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.max_iterations = 5  # Limit to 5 loops to prevent runaway costs

    def _execute_tool(self, tool_name: str, args: str) -> str:
        # Mock tool execution registry. In future phases, this will use real tools.
        if tool_name == "web_search":
            return f"Found search results for: {args}"
        elif tool_name == "calculate":
            return f"Calculated result: 42"
        return f"[Error]: Tool {tool_name} not found."

    def execute(self, task: str, context: Dict[str, Any]) -> str:
        """
        Executes an autonomous ReAct (Reasoning and Acting) loop using the real LLM router.
        """
        log.info(f"Sub-agent '{self.name}' executing task: {task[:50]}...")

        try:
            from src.core.ai_router import AIRouter
            router = AIRouter()
        except ImportError:
            return "Task failed: Could not load AIRouter."

        memory_scratchpad = ""
        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1
            log.info(f"[{self.name}] Loop iteration {iterations}/{self.max_iterations}")

            prompt = f"""You are executing an autonomous task loop.
Task: {task}
Current Scratchpad:
{memory_scratchpad}

Decide your next move. You must reply in this exact format:
Thought: <your reasoning>\nAction: <web_search|calculate|finish>
Action Input: <the argument for the action, or the final answer if action is finish>"""

            try:
                # Use the real AI Router
                result = router.generate(self.system_prompt, prompt, nvidia_task_type="reasoning")
                response_text = result.text
            except Exception as e:
                return f"Task failed during LLM generation: {str(e)}"

            # Parse the LLM's response
            thought_match = re.search(r"Thought: (.*)", response_text)
            action_match = re.search(r"Action: (.*)", response_text)
            input_match = re.search(r"Action Input: (.*)", response_text)

            thought = thought_match.group(1) if thought_match else "No thought provided."
            action = action_match.group(1).strip().lower() if action_match else "finish"
            action_input = input_match.group(1).strip() if input_match else ""

            memory_scratchpad += f"\nThought: {thought}\nAction: {action}({action_input})"

            if action == "finish" or action == "none":
                return f"Task completed: {action_input}"

            # Execute the tool and append observation
            observation = self._execute_tool(action, action_input)
            memory_scratchpad += f"\nObservation: {observation}"

        return "Task failed: Max iterations reached without a final answer."

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
