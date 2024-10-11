import pytest

from ai_shell.utils.cache import check_cache, clear_cache, init_cache, save_cache


@pytest.mark.asyncio
async def test_cache_operations():
    await init_cache()

    # Test saving to cache
    await save_cache("test_command", "echo 'Hello'", "Hello")

    # Test retrieving from cache
    cached_command, cached_output = await check_cache("test_command")
    assert cached_command == "echo 'Hello'"
    assert cached_output == "Hello"

    # Test clearing cache
    await clear_cache()
    cached_command, cached_output = await check_cache("test_command")
    assert cached_command is None
    assert cached_output is None


# Adicione mais testes para as operações de cache conforme necessário
