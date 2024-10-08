# utils/cache.py
import time

import aiosqlite


async def init_cache():
    async with aiosqlite.connect("cache.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                prompt TEXT PRIMARY KEY,
                output TEXT,
                timestamp REAL
            )
        """)
        await db.commit()


async def check_cache(prompt: str) -> str | None:
    async with aiosqlite.connect("cache.db") as db:
        cursor = await db.execute(
            "SELECT output, timestamp FROM cache WHERE prompt = ?", (prompt,)
        )
        result = await cursor.fetchone()
        if result:
            output, timestamp = result
            if time.time() - timestamp < 3600:  # 1 hora de expiração
                return output
    return None


async def save_cache(prompt: str, output: str):
    async with aiosqlite.connect("cache.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO cache (prompt, output, timestamp) VALUES (?, ?, ?)",
            (prompt, output, time.time()),
        )
        await db.commit()


async def clean_expired_cache(expiration_time: int = 3600):
    async with aiosqlite.connect("cache.db") as db:
        await db.execute(
            "DELETE FROM cache WHERE ? - timestamp > ?", (time.time(), expiration_time)
        )
        await db.commit()


async def clear_cache():
    async with aiosqlite.connect("cache.db") as db:
        await db.execute("DELETE FROM cache")
        await db.commit()
