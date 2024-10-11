from unittest.mock import AsyncMock, patch

import pytest

from ai_shell.ai_shell import AIShell
from ai_shell.datatypes import AIShellResult


@pytest.fixture
async def ai_shell():
    with patch("ai_shell.ai_shell.CommandGenerator"), patch(
        "ai_shell.ai_shell.CommandExecutor"
    ), patch("ai_shell.ai_shell.UIHandler"):
        shell = await AIShell.create(non_interactive=True, dry_run=True)
        yield shell


@pytest.mark.asyncio
async def test_process_command_success(ai_shell):
    ai_shell.command_generator.generate_command = AsyncMock(
        return_value=("echo 'Hello, World!'", 10, "test_model")
    )
    ai_shell.command_executor.execute_command = AsyncMock(
        return_value=("Hello, World!", 0)
    )
    ai_shell.ui_handler.confirm_execution = AsyncMock(return_value="execute")

    result = await ai_shell.process_command("Say hello")

    assert isinstance(result, AIShellResult)
    assert result.success
    assert result.message == "Hello, World!"


@pytest.mark.asyncio
async def test_process_command_failure(ai_shell):
    ai_shell.command_generator.generate_command = AsyncMock(
        return_value=("invalid_command", 10, "test_model")
    )
    ai_shell.command_executor.execute_command = AsyncMock(
        return_value=("Command not found", 1)
    )
    ai_shell.ui_handler.confirm_execution = AsyncMock(return_value="execute")

    result = await ai_shell.process_command("Run invalid command")

    assert isinstance(result, AIShellResult)
    assert not result.success
    assert "Command not found" in result.message
