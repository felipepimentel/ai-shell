from unittest.mock import patch

import pytest

from ai_shell.ai_shell import AIShell


@pytest.fixture
async def ai_shell():
    with patch("ai_shell.ai_shell.CommandGenerator"), patch(
        "ai_shell.ai_shell.CommandExecutor"
    ), patch("ai_shell.ai_shell.UIHandler"):
        shell = await AIShell.create(non_interactive=True, dry_run=True)
        yield shell
