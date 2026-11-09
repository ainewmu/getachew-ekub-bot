import json
import random
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import asyncpg
from config import DEFAULT_VEHICLES, DEFAULT_BANKS, DATABASE_URL

pool = None


class TicketsTaken(Exception):
    pass


def _clean_dsn(dsn: str) -> str:
    p = urlsplit(dsn.strip().strip("'\""))
    q = [(k, v) for k, v in parse_qsl(p.query) if k not in ("sslmode", "channel_binding")]
    return urlunsplit(p._replace(query=urlencode(q)))


async def init_db():
    global pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Add it in Render > Environment.")
    pool = await asyncpg.create_pool(
        _clean_dsn(DATABASE_URL), ssl="require", min_size=1, max_size=5,
        statement_cache_size=0, max_inactive_connection_lifetime=30,
    )
    async with pool.acquire() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, name_am TEXT, name_or TEXT, subtitle TEXT,
                price INTEGER NOT NULL, total_tickets INTEGER NOT NULL, image TEXT,
                is_active INTEGER DEFAULT 1, sold_tickets INTEGER DEFAULT 0, countdown_end BIGINT
            );
            CREATE TABLE IF NOT EXISTS ticket_status (
                vehicle_id INTEGER, ticket_number INTEGER, is_available INTEGER DEFAULT 1,
                PRIMARY KEY (vehicle_id, ticket_number)
            );
            CREATE TABLE IF NOT EXISTS banks (
                id SERIAL PRIMARY KEY, name TEXT NOT NULL, account TEXT NOT NULL, holder TEXT
            );
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY, user_id BIGINT, vehicle_id INTEGER, tickets TEXT, total_amount INTEGER,
                full_name TEXT, phone TEXT, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        """)
        if await db.fetchval("SELECT COUNT(*) FROM vehicles") == 0:
            end = int((time.time() + 30 * 86400) * 1000)
            for v in DEFAULT_VEHICLES:
                total = v["total_tickets"]
                avail = set(random.sample(range(1, total + 1), max(1, int(total * 0.05))))
                await db.execute(
                    """INSERT INTO vehicles (id, name, name_am, name_or, subtitle, price, total_tickets, image, is_active, sold_tickets, countdown_end)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,1,$9,$10)""",
                    v["id"], v["name"], v["name_am"], v["name_or"], v["subtitle"], v["price"],
                    total, v["image"], total - len(avail), end)
                await db.executemany(
                    "INSERT INTO ticket_status (vehicle_id, ticket_number, is_available) VALUES ($1,$2,$3)",
                    [(v["id"], n, 1 if n in avail else 0) for n in range(1, total + 1)])
        if await db.fetchval("SELECT COUNT(*) FROM banks") == 0:
            for b in DEFAULT_BANKS:
                await db.execute("INSERT INTO banks (name, account, holder) VALUES ($1,$2,$3)", b["name"], b["account"], b["holder"])


async def _recount(db, vid: int):
    avail = await db.fetchval("SELECT COUNT(*) FROM ticket_status WHERE vehicle_id=$1 AND is_available=1", vid)
    total = await db.fetchval("SELECT total_tickets FROM vehicles WHERE id=$1", vid)
    await db.execute("UPDATE vehicles SET sold_tickets=$1 WHERE id=$2", (total or 0) - avail, vid)


async def get_vehicles():
    async with pool.acquire() as db:
        return [dict(r) for r in await db.fetch("SELECT * FROM vehicles WHERE is_active = 1 ORDER BY id")]


async def get_vehicle(vehicle_id: int):
    async with pool.acquire() as db:
        r = await db.fetchrow("SELECT * FROM vehicles WHERE id = $1", vehicle_id)
        return dict(r) if r else None


async def get_ticket_status(vehicle_id: int, page: int = 1, per_page: int = 100):
    async with pool.acquire() as db:
        rows = await db.fetch(
            "SELECT ticket_number, is_available FROM ticket_status WHERE vehicle_id=$1 ORDER BY ticket_number LIMIT $2 OFFSET $3",
            vehicle_id, per_page, (page - 1) * per_page)
        return [dict(r) for r in rows]


async def get_available_count(vehicle_id: int):
    async with pool.acquire() as db:
        return await db.fetchval("SELECT COUNT(*) FROM ticket_status WHERE vehicle_id=$1 AND is_available=1", vehicle_id)


async def get_banks():
    async with pool.acquire() as db:
        return [dict(r) for r in await db.fetch("SELECT * FROM banks ORDER BY id")]


async def update_vehicle(vehicle_id: int, data: dict):
    keys = ["name", "name_am", "name_or", "subtitle", "price", "total_tickets", "image", "is_active", "countdown_end"]
    sets, vals = [], []
    for k in keys:
        if k in data:
            vals.append(data[k])
            sets.append(f"{k} = ${len(vals)}")
    async with pool.acquire() as db:
        async with db.transaction():
            if sets:
                vals.append(vehicle_id)
                await db.execute(f"UPDATE vehicles SET {', '.join(sets)} WHERE id = ${len(vals)}", *vals)
            if "total_tickets" in data:
                total = data["total_tickets"]
                cur = await db.fetchval("SELECT COALESCE(MAX(ticket_number),0) FROM ticket_status WHERE vehicle_id=$1", vehicle_id)
                if total > cur:
                    await db.executemany(
                        "INSERT INTO ticket_status (vehicle_id, ticket_number, is_available) VALUES ($1,$2,1)",
                        [(vehicle_id, n) for n in range(cur + 1, total + 1)])
                elif total < cur:
                    await db.execute("DELETE FROM ticket_status WHERE vehicle_id=$1 AND ticket_number>$2", vehicle_id, total)
                await _recount(db, vehicle_id)


async def update_banks(banks: list):
    async with pool.acquire() as db:
        async with db.transaction():
            await db.execute("DELETE FROM banks")
            for b in banks:
                await db.execute("INSERT INTO banks (name, account, holder) VALUES ($1,$2,$3)",
                                 b["name"], b["account"], b.get("holder", ""))


async def create_order(user_id: int, vehicle_id: int, tickets: list, total: int, full_name: str, phone: str):
    tickets = sorted(set(tickets))
    async with pool.acquire() as db:
        async with db.transaction():
            taken = await db.fetchval(
                """WITH u AS (UPDATE ticket_status SET is_available = 0
                              WHERE vehicle_id=$1 AND ticket_number = ANY($2::int[]) AND is_available = 1 RETURNING 1)
                   SELECT COUNT(*) FROM u""", vehicle_id, tickets)
            if taken != len(tickets):
                raise TicketsTaken()
            await db.execute(
                "INSERT INTO orders (user_id, vehicle_id, tickets, total_amount, full_name, phone) VALUES ($1,$2,$3,$4,$5,$6)",
                user_id, vehicle_id, json.dumps(tickets), total, full_name, phone)
            await _recount(db, vehicle_id)


async def release_chosen(vehicle_id: int):
    """Make every number chosen by customers available again."""
    async with pool.acquire() as db:
        async with db.transaction():
            rows = await db.fetch("SELECT tickets FROM orders WHERE vehicle_id=$1 AND status <> 'released'", vehicle_id)
            nums = set()
            for r in rows:
                nums.update(json.loads(r["tickets"]))
            if nums:
                await db.execute("UPDATE ticket_status SET is_available=1 WHERE vehicle_id=$1 AND ticket_number = ANY($2::int[])",
                                 vehicle_id, list(nums))
            await db.execute("UPDATE orders SET status='released' WHERE vehicle_id=$1", vehicle_id)
            await _recount(db, vehicle_id)
            return len(nums)


async def get_settings():
    async with pool.acquire() as db:
        return {r["key"]: r["value"] for r in await db.fetch("SELECT key, value FROM settings")}


async def set_setting(key: str, value: str):
    async with pool.acquire() as db:
        await db.execute("INSERT INTO settings (key, value) VALUES ($1,$2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", key, value)
