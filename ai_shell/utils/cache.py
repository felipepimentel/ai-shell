import time
from typing import Tuple

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
    async with aiosqlite.connect("cache.db") as db:
        cursor = await db.execute(
            "SELECT generated_command, output, timestamp FROM cache WHERE prompt = ?",
            (prompt,),
        )
        result = await cursor.fetchone()

        if result:
            generated_command, output, timestamp = result
            if time.time() - timestamp < 3600:  # 1 hora de expiração
                return generated_command, output
            else:
                print("Cache expirado.")
        else:
            print(f"Nenhum resultado encontrado no cache para o prompt: {prompt}")
    return None, None


async def save_cache(command: str, output: str):
    async with aiosqlite.connect("cache.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO cache (prompt, generated_command, output, timestamp) VALUES (?, ?, ?, ?)",
            (command, None, output, time.time()),
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
