import ast
import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

log = logging.getLogger(__name__)

class WorkflowEngine:
    """
    JARVIS Phase 4 (Feature 4.2 & 4.3): NLP Workflow Engine.
    Parses natural language requests into a JSON DAG (Directed Acyclic Graph)
    of nodes (Triggers, Actions, Logic) and executes them sequentially.
    Includes a self-healing retry mechanism.
    """
    def __init__(self, supabase_client, ai_router):
        self.supabase = supabase_client
        self.ai = ai_router

    def _safe_eval(self, expr: str) -> Any:
        """
        Safely evaluates a pseudo-code condition using AST parsing.
        Only allows basic comparisons, constants, and boolean logic.
        """
        try:
            tree = ast.parse(expr, mode='eval')

            def _eval_node(node):
                if isinstance(node, ast.Expression):
                    return _eval_node(node.body)
                elif isinstance(node, ast.Constant):
                    return node.value
                elif isinstance(node, ast.Compare):
                    current_left = _eval_node(node.left)
                    for op, right_node in zip(node.ops, node.comparators):
                        right = _eval_node(right_node)
                        if isinstance(op, ast.Eq):
                            if not (current_left == right): return False
                        elif isinstance(op, ast.NotEq):
                            if not (current_left != right): return False
                        elif isinstance(op, ast.Lt):
                            if not (current_left < right): return False
                        elif isinstance(op, ast.LtE):
                            if not (current_left <= right): return False
                        elif isinstance(op, ast.Gt):
                            if not (current_left > right): return False
                        elif isinstance(op, ast.GtE):
                            if not (current_left >= right): return False
                        elif isinstance(op, ast.In):
                            if not (current_left in right): return False
                        elif isinstance(op, ast.NotIn):
                            if not (current_left not in right): return False
                        else:
                            raise ValueError(f"Unsupported operator: {type(op)}")
                        current_left = right
                    return True
                elif isinstance(node, ast.BoolOp):
                    values = [_eval_node(v) for v in node.values]
                    if isinstance(node.op, ast.And):
                        return all(values)
                    elif isinstance(node.op, ast.Or):
                        return any(values)
                elif isinstance(node, ast.UnaryOp):
                    operand = _eval_node(node.operand)
                    if isinstance(node.op, ast.Not):
                        return not operand

                raise ValueError(f"Unsupported AST node: {type(node)}")

            return _eval_node(tree)
        except Exception as e:
            log.error(f"Safe eval error: {e}")
            return False

    def build_from_nl(self, description: str) -> Optional[str]:
        """
        Parses a natural language description into a Workflow DAG and saves it.
        """
        if not self.supabase:
            return None

        prompt = f"""
        Ajay wants to automate a new routine: "{description}"

        Translate this into a strict JSON Directed Acyclic Graph (DAG) for a workflow engine.
        Available Node Types: 'trigger.cron', 'trigger.webhook', 'trigger.email', 'action.http_request', 'action.telegram_message', 'action.agent_task', 'logic.condition'

        Return ONLY valid JSON with no backticks:
        {{
            "title": "Short title",
            "description": "Full description of the routine",
            "trigger_type": "cron", // e.g., 'cron', 'email'
            "trigger_config": {{"schedule": "0 9 * * *"}}, // e.g., standard cron syntax
            "nodes": [
                {{"id": "node_1", "type": "action.agent_task", "config": {{"prompt": "Check my emails and summarize urgent ones."}}}},
                {{"id": "node_2", "type": "logic.condition", "config": {{"condition": "{{node_1.output}} contains 'urgent'"}}}},
                {{"id": "node_3", "type": "action.telegram_message", "config": {{"message": "Urgent Emails: {{node_1.output}}"}}}}
            ],
            "edges": [
                {{"source": "node_1", "target": "node_2"}},
                {{"source": "node_2", "target": "node_3", "condition": "true"}} // only execute target if condition node is true
            ]
        }}
        """

        try:
            result = self.ai.generate(
                system_prompt="You are a strict JSON data parser mapping natural language to Workflow AST nodes.",
                user_message=prompt
            )

            match = re.search(r'\{.*\}', result.text, re.DOTALL)
            if not match:
                return None

            data = json.loads(match.group(0))

            # Save the workflow definition to the database
            res = self.supabase.table("aisha_workflows").insert({
                "title": data["title"],
                "description": data["description"],
                "trigger_type": data["trigger_type"],
                "trigger_config": data["trigger_config"],
                "nodes": data["nodes"],
                "edges": data["edges"]
            }).execute()

            w_id = res.data[0]["id"]

            summary = f"✨ *Workflow Created:* {data['title']}\n"
            summary += f"*{data['description']}*\n"
            summary += f"Trigger: `{data['trigger_type']}` (`{json.dumps(data['trigger_config'])}`)\n"
            summary += f"Steps: {len(data['nodes'])}\n\n"
            summary += "*(This automation will now run in the background. If a step fails, I will use AI to attempt self-healing!)*"

            return summary

        except Exception as e:
            log.error(f"Workflow NLP Builder Error: {e}")
            return None

    def _execute_node(self, node: Dict[str, Any], state: Dict[str, Any]) -> Any:
        """Simulates executing a single node's logic."""
        node_type = node.get("type", "")
        config = node.get("config", {})

        # Simple template resolution {{var}}
        resolved_config = json.dumps(config)
        for key, value in state.items():
            resolved_config = resolved_config.replace(f"{{{{{key}}}}}", str(value))
        config = json.loads(resolved_config)

        if node_type == "action.telegram_message":
            # Just print for the prototype
            log.info(f"[Workflow] Telegram sent: {config.get('message')}")
            return True

        elif node_type == "action.agent_task":
            # Hand off to LLM
            res = self.ai.generate("You are completing a workflow task.", config.get("prompt", ""))
            return res.text

        elif node_type == "logic.condition":
            try:
                # Basic string replacement for pseudo-code
                cond = config.get("condition", "False")
                cond = cond.replace("contains", "in")
                return self._safe_eval(cond)
            except Exception:
                return False

        elif node_type == "action.http_request":
            import urllib.request
            req = urllib.request.Request(config.get("url", ""), method=config.get("method", "GET"))
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.read().decode('utf-8')

        return None

    def execute_workflow(self, workflow_id: str) -> bool:
        """
        Executes a workflow graph using a topological approach.
        Includes Feature 4.3: Self-healing error correction.
        """
        if not self.supabase:
            return False

        try:
            # 1. Fetch workflow
            wf_res = self.supabase.table("aisha_workflows").select("*").eq("id", workflow_id).execute()
            if not wf_res.data:
                return False

            wf = wf_res.data[0]
            nodes = {n["id"]: n for n in wf.get("nodes", [])}
            edges = wf.get("edges", [])

            # 2. Record execution start
            exec_res = self.supabase.table("aisha_workflow_executions").insert({
                "workflow_id": workflow_id,
                "status": "running"
            }).execute()
            exec_id = exec_res.data[0]["id"]

            log.info(f"[Workflow] Starting execution of {wf['title']} (ID: {exec_id})")

            # 3. Naive Sequential Execution for Prototype (Topological Sort in Production)
            # We assume nodes list is already in sequential order from the LLM for simplicity.
            state = {} # Holds the output of each node

            for node_id, node in nodes.items():
                try:
                    log.info(f"[Workflow] Executing node {node_id} ({node['type']})")
                    output = self._execute_node(node, state)
                    state[f"{node_id}.output"] = output

                except Exception as step_error:
                    log.warning(f"[Workflow] Node {node_id} failed: {step_error}. Attempting Self-Heal...")

                    # Update status to self_healing
                    self.supabase.table("aisha_workflow_executions").update({"status": "self_healing"}).eq("id", exec_id).execute()

                    # 4. Self-Healing Phase
                    heal_prompt = f"""
                    The workflow step "{node['type']}" failed during execution.
                    Configuration: {json.dumps(node['config'])}
                    Error: {str(step_error)}

                    Provide a fixed Configuration JSON for this node to make it succeed next time.
                    Return ONLY the new config JSON, no backticks.
                    """
                    heal_res = self.ai.generate("You are an expert systems engineer fixing broken configurations.", heal_prompt)

                    try:
                        match = re.search(r'\{.*\}', heal_res.text, re.DOTALL)
                        if match:
                            fixed_config = json.loads(match.group(0))
                            node['config'] = fixed_config
                            # Retry execution
                            output = self._execute_node(node, state)
                            state[f"{node_id}.output"] = output
                            log.info(f"[Workflow] Self-heal successful for {node_id}")

                            # Save the fixed config back to the original workflow
                            self.supabase.table("aisha_workflows").update({"nodes": list(nodes.values())}).eq("id", workflow_id).execute()
                        else:
                            raise Exception("LLM did not provide a fix.")
                    except Exception as heal_error:
                        log.error(f"[Workflow] Self-heal failed: {heal_error}. Halting workflow.")
                        self.supabase.table("aisha_workflow_executions").update({
                            "status": "failed",
                            "error_message": f"Node {node_id} failed: {step_error}",
                            "finished_at": datetime.now(timezone.utc).isoformat()
                        }).eq("id", exec_id).execute()
                        return False

            # 5. Success
            self.supabase.table("aisha_workflow_executions").update({
                "status": "completed",
                "state_snapshot": state,
                "finished_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", exec_id).execute()

            log.info(f"[Workflow] Execution {exec_id} completed successfully.")
            return True

        except Exception as e:
            log.error(f"Workflow Execution Error: {e}")
            return False
