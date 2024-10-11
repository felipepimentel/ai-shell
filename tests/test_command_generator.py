import pytest
from unittest.mock import AsyncMock, patch
from ai_shell.command.command_generator import CommandGenerator

@pytest.fixture
def command_generator():
    return CommandGenerator()

@pytest.mark.asyncio
async def test_generate_command_success(command_generator):
    with patch('ai_shell.llm.prompts.generate_command_from_prompt', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = ("echo 'Hello, World!'", 10, "test_model")
        
        result = await command_generator.generate_command("Say hello", {})
        
        assert result == ("echo 'Hello, World!'", 10, "test_model")
        mock_generate.assert_called_once_with("Say hello", {})

@pytest.mark.asyncio
async def test_generate_command_failure(command_generator):
    with patch('ai_shell.llm.prompts.generate_command_from_prompt', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = (None, None, None)
        
        result = await command_generator.generate_command("Invalid command", {})
        
        assert result == (None, None, None)
        mock_generate.assert_called_once_with("Invalid command", {})

# Novo teste para verificar o comportamento com um comando complexo
@pytest.mark.asyncio
async def test_generate_command_complex(command_generator):
    complex_command = "Find all Python files in the current directory, excluding tests, and count the lines of code"
    expected_output = ("find . -name '*.py' ! -path '*/test*' | xargs wc -l", 15, "test_model")
    
    with patch('ai_shell.llm.prompts.generate_command_from_prompt', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = expected_output
        
        result = await command_generator.generate_command(complex_command, {})
        
        assert result == expected_output
        mock_generate.assert_called_once_with(complex_command, {})

# Adicione mais testes conforme necessário