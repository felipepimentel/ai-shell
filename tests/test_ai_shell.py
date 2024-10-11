import pytest
from unittest.mock import AsyncMock, patch
from ai_shell.ai_shell import AIShell
from ai_shell.datatypes import AIShellResult
from ai_shell.utils.conflict_resolver import ConflictResolution

@pytest.fixture
def ai_shell():
    return AIShell(non_interactive=True, dry_run=True)

@pytest.mark.asyncio
async def test_process_command_success(ai_shell):
    ai_shell.command_generator.generate_command = AsyncMock(return_value=("echo 'Hello, World!'", 10, "test_model"))
    ai_shell.command_executor.execute_command = AsyncMock(return_value=("Hello, World!", 0))
    ai_shell.ui_handler.confirm_execution = AsyncMock(return_value="")

    result = await ai_shell.process_command("Say hello")

    assert isinstance(result, AIShellResult)
    assert result.success == True
    assert result.message == "Hello, World!"

@pytest.mark.asyncio
async def test_process_command_failure(ai_shell):
    ai_shell.command_generator.generate_command = AsyncMock(return_value=("invalid_command", 10, "test_model"))
    ai_shell.command_executor.execute_command = AsyncMock(return_value=("Command not found", 1))
    ai_shell.ui_handler.confirm_execution = AsyncMock(return_value="")

    result = await ai_shell.process_command("Run invalid command")

    assert isinstance(result, AIShellResult)
    assert result.success == False
    assert result.message == "Command not found"

# ... (resto dos testes permanecem os mesmos)