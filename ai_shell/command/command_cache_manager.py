from collections import OrderedDict
from typing import Optional, Tuple

from ..utils.cache import check_cache, clean_expired_cache, save_cache


class CommandCacheManager:
    def __init__(self) -> None:
        self.command_cache: OrderedDict[str, str] = OrderedDict()
        self.max_cache_size = 100

    async def check_cache(self, command: str) -> Tuple[Optional[str], Optional[str]]:
        return await check_cache(command)

    async def cache_command(
        self, command: str, generated_command: str, output: str
    ) -> None:
        await save_cache(command, generated_command, output)
        self.add_to_cache(command, output)

    def add_to_cache(self, command: str, output: str) -> None:
        if len(self.command_cache) >= self.max_cache_size:
            self.command_cache.popitem(last=False)
        self.command_cache[command] = output

    async def clean_expired_cache(self) -> None:
        await clean_expired_cache()

    async def clear_cache(self) -> None:
        self.command_cache.clear()
        await clean_expired_cache()
