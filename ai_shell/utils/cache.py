from __future__ import annotations

import time
from typing import Tuple, Callable, Any
from functools import wraps

import aiosqlite


async def init_cache():
    async with aiosqlite.connect("cache.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                prompt TEXT PRIMARY KEY,
                generated_command TEXT,  -- Armazenar o comando gerado
                output TEXT,
                timestamp REAL
            )
        """)
        await db.commit()


async def check_cache(prompt: str) -> Tuple[str | None, str | None]:
    """
    Retorna uma tupla (comando_gerado, saída), ou (None, None) se não encontrado.
    """
    await init_cache()  # Ensure the table exists before querying
    async with aiosqlite.connect("cache.db") as db:
        cursor = await db.execute(
            "SELECT generated_command, output, timestamp FROM cache WHERE prompt = ?",
            (prompt,),
        )
        result = await cursor.fetchone()

        if result:
            generated_command, output, timestamp = result
            if time.time() - timestamp < 3600:
                return generated_command, output
    return None, None


async def save_cache(command: str, generated_command: str, output: Any):
    # Converta o output para string se não for None
    output_str = str(output) if output is not None else ""
    
    await init_cache()  # Ensure the table exists before inserting
    async with aiosqlite.connect("cache.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO cache (prompt, generated_command, output, timestamp) VALUES (?, ?, ?, ?)",
            (command, generated_command, output_str, time.time()),
        )
        await db.commit()


async def clean_expired_cache():
    async with aiosqlite.connect("cache.db") as db:
        await db.execute("DELETE FROM cache WHERE timestamp < ?", (time.time() - 3600,))
        await db.commit()


async def clear_cache():
    async with aiosqlite.connect("cache.db") as db:
        await db.execute("DELETE FROM cache")
        await db.commit()


def cache_result(func: Callable) -> Callable:
    """
    A decorator that caches the result of a function.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Generate a cache key based on the function name and arguments
        cache_key = f"{func.__name__}:{args}:{kwargs}"
        
        # Check if the result is in the cache
        cached_result, _ = await check_cache(cache_key)
        if cached_result:
            return cached_result

        # If not in cache, call the function
        result = await func(*args, **kwargs)

        # Save the result to the cache
        await save_cache(cache_key, "", str(result))

        return result

    return wrapper
