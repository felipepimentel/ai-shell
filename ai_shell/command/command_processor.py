from ..config import config
from ..llm import ai, build_contextual_prompt
from ..utils.os_api import get_system_info
from ..utils.cache import check_cache, save_cache
from ..utils.console import (
    print_error_message,
    print_success_message,
    print_verbose_message,
)
from .command_executor import execute_command
from .command_history import append_to_history
from .safety_checker import is_command_safe


async def replace_aliases(command: str) -> str:
    """
    Substitui um alias pelo comando completo correspondente, se existir.
    """
    for alias, full_command in config.aliases.items():
        if command.startswith(alias):
            return command.replace(alias, full_command, 1)
    return command


async def process_command(context: CommandContext) -> str | None:
    """
    Processa um comando fornecido pelo usuário, substitui aliases, checa cache,
    executa o comando e armazena o resultado no cache e no histórico.
    """
    if context.verbose:
        print_verbose_message(f"Processing command: {context.prompt_text}")

    context.prompt_text = await replace_aliases(context.prompt_text)
    system_info = get_system_info()

    async with context.cache_lock:
        cached_output = await check_cache(context.conn, context.prompt_text)
    if cached_output:
        print_success_message(f"Using cached result: {cached_output}")
        return cached_output

    full_prompt = (
        await build_contextual_prompt(context.history)
        + f"Instruction: {context.prompt_text}"
    )
    ai_response = await ai.generate_command(full_prompt, system_info)

    if not ai_response:
        print_error_message("Error generating command.")
        return

    if not await is_command_safe(ai_response):
        print_error_message("Aborting potentially dangerous command.")
        return

    output, error = await execute_command(ai_response, context.simulation_mode)

    if error:
        print_error_message(f"Command error: {error}")
        append_to_history(context.history, ai_response, error)
        return

    print_success_message(f"Command output: {output}")
    append_to_history(context.history, ai_response, output)

    async with context.cache_lock:
        await save_cache(context.conn, context.prompt_text, output)

    return f"Next step based on output: {output}"
