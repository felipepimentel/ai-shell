from typing import List, Dict, Any
from ai_shell.handlers.dependency_handler import check_and_install_dependency, install_dependency
from ai_shell.command.command_executor import CommandExecutor
from ai_shell.utils.logger import get_logger

logger = get_logger("ai_shell.workflow_manager")

class WorkflowManager:
    def __init__(self, command_executor: CommandExecutor):
        self.current_workflow: List[Dict[str, Any]] = []
        self.command_executor = command_executor

    async def add_step(self, command: str, dependencies: List[str] = None):
        self.current_workflow.append({
            "command": command,
            "dependencies": dependencies or [],
            "status": "pending",
            "output": "",
            "error": None
        })

    async def execute_workflow(self):
        for i, step in enumerate(self.current_workflow):
            if step["status"] == "pending":
                success = await self.execute_step(step)
                if not success:
                    logger.error(f"Workflow execution failed at step {i+1}: {step['command']}")
                    return False
            logger.info(f"Completed step {i+1}/{len(self.current_workflow)}")
        logger.info("Workflow executed successfully")
        return True

    async def execute_step(self, step: Dict[str, Any]) -> bool:
        try:
            for dep in step["dependencies"]:
                if not await check_and_install_dependency(dep):
                    logger.error(f"Failed to install dependency: {dep}")
                    step["status"] = "failed"
                    step["error"] = f"Dependency installation failed: {dep}"
                    return False

            output, return_code = await self.command_executor.execute_command(step["command"], timeout=300)
            step["output"] = output
            success = return_code == 0
            step["status"] = "completed" if success else "failed"
            if not success:
                step["error"] = f"Command failed with return code {return_code}"
                logger.error(f"Step execution failed: {step['command']}")
                logger.error(f"Output: {output}")
            return success
        except Exception as e:
            logger.error(f"Error executing step: {str(e)}")
            step["status"] = "failed"
            step["error"] = f"Step execution error: {str(e)}"
            return False

    async def resume_workflow(self):
        for i, step in enumerate(self.current_workflow):
            if step["status"] == "pending":
                logger.info(f"Resuming workflow from step {i+1}: {step['command']}")
                return await self.execute_workflow()
        logger.info("No pending steps found. Workflow is complete.")
        return True

    async def pause_workflow(self):
        for step in self.current_workflow:
            if step["status"] == "pending":
                return True
        return False

    def get_workflow_status(self) -> Dict[str, Any]:
        total_steps = len(self.current_workflow)
        completed_steps = sum(1 for step in self.current_workflow if step["status"] == "completed")
        failed_steps = sum(1 for step in self.current_workflow if step["status"] == "failed")
        return {
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "progress": f"{completed_steps}/{total_steps}",
            "status": "In Progress" if completed_steps < total_steps else "Completed"
        }

    async def handle_error_and_resume(self, step: Dict[str, Any], error: Exception) -> bool:
        logger.error(f"Error occurred during step execution: {step['command']}")
        logger.error(f"Error details: {str(error)}")

        resolved = await self.attempt_error_resolution(error)

        if resolved:
            logger.info(f"Error resolved. Resuming workflow from step: {step['command']}")
            return await self.execute_step(step)
        else:
            logger.error(f"Unable to resolve error. Workflow execution stopped.")
            return False

    async def attempt_error_resolution(self, error: Exception) -> bool:
        if isinstance(error, ImportError):
            # Attempt to install the missing module
            module_name = str(error).split("'")[1]
            logger.info(f"Attempting to install missing module: {module_name}")
            success = await install_dependency(module_name)
            return success
        elif isinstance(error, PermissionError):
            logger.warning("Permission error encountered. Consider running the command with elevated privileges.")
            return False
        # Add more error resolution strategies as needed
        return False