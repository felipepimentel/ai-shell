import pytest
from ai_shell.utils.conflict_resolver import detect_conflict, resolve_conflict, ConflictResolution

@pytest.mark.asyncio
async def test_detect_conflict_git_clone(tmp_path):
    existing_dir = tmp_path / "existing_dir"
    existing_dir.mkdir()
    command = f"git clone https://github.com/test/repo {existing_dir}"
    conflict = await detect_conflict(command)
    assert conflict == f"Path already exists: {existing_dir}"

@pytest.mark.asyncio
async def test_detect_conflict_mkdir(tmp_path):
    existing_dir = tmp_path / "existing_dir"
    existing_dir.mkdir()
    command = f"mkdir {existing_dir}"
    conflict = await detect_conflict(command)
    assert conflict == f"Path already exists: {existing_dir}"

@pytest.mark.asyncio
async def test_detect_conflict_no_conflict():
    command = "echo 'Hello, World!'"
    conflict = await detect_conflict(command)
    assert conflict is None

@pytest.mark.asyncio
async def test_resolve_conflict_remove_and_clone():
    conflict = "Path already exists: /tmp/test_repo"
    resolution = ConflictResolution.REMOVE_AND_CLONE
    original_command = "git clone https://github.com/test/repo /tmp/test_repo"
    
    result = await resolve_conflict(conflict, resolution, original_command)
    assert result == original_command

@pytest.mark.asyncio
async def test_resolve_conflict_clone_different_location():
    conflict = "Path already exists: /tmp/test_repo"
    resolution = ConflictResolution.CLONE_DIFFERENT_LOCATION
    original_command = "git clone https://github.com/test/repo /tmp/test_repo"
    
    result = await resolve_conflict(conflict, resolution, original_command)
    assert "/tmp/test_repo_new" in result

# Adicione mais testes para o conflict_resolver conforme necessário