import aiosqlite
import json
import random
from pathlib import Path
from config import DEFAULT_VEHICLES, DEFAULT_BANKS

DB_PATH = Path(__file__).parent / "data" / "ekub.db"

async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                name_am TEXT,
                name_or TEXT,
                subtitle TEXT,
                price INTEGER NOT NULL,
                total_tickets INTEGER NOT NULL,
                image TEXT,
                is_active INTEGER DEFAULT 1,
                sold_tickets INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_status (
                vehicle_id INTEGER,
                ticket_number INTEGER,
                is_available INTEGER DEFAULT 1,
                PRIMARY KEY (vehicle_id, ticket_number)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS banks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                account TEXT NOT NULL,
                holder TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                vehicle_id INTEGER,
                tickets TEXT,
                total_amount INTEGER,
                full_name TEXT,
                phone TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

        # Seed vehicles if empty
        cursor = await db.execute("SELECT COUNT(*) FROM vehicles")
        count = (await cursor.fetchone())[0]
        if count == 0:
            for v in DEFAULT_VEHICLES:
                await db.execute(
                    """INSERT INTO vehicles (id, name, name_am, name_or, subtitle, price, total_tickets, image, is_active, sold_tickets)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (v["id"], v["name"], v["name_am"], v["name_or"], v["subtitle"], v["price"],
                     v["total_tickets"], v["image"], 1, int(v["total_tickets"] * 0.95))
                )
                # Mark 95% as unavailable randomly
                total = v["total_tickets"]
                available_count = max(1, int(total * 0.05))
                all_numbers = list(range(1, total + 1))
                available = set(random.sample(all_numbers, available_count))
                for num in all_numbers:
                    is_avail = 1 if num in available else 0
                    await db.execute(
                        "INSERT INTO ticket_status (vehicle_id, ticket_number, is_available) VALUES (?, ?, ?)",
                        (v["id"], num, is_avail)
                    )
            await db.commit()

        # Seed banks if empty
        cursor = await db.execute("SELECT COUNT(*) FROM banks")
        count = (await cursor.fetchone())[0]
        if count == 0:
            for b in DEFAULT_BANKS:
                await db.execute(
                    "INSERT INTO banks (name, account, holder) VALUES (?, ?, ?)",
                    (b["name"], b["account"], b["holder"])
                )
            await db.commit()


async def get_vehicles():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM vehicles WHERE is_active = 1 ORDER BY id")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_vehicle(vehicle_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_ticket_status(vehicle_id: int, page: int = 1, per_page: int = 100):
    offset = (page - 1) * per_page
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT ticket_number, is_available FROM ticket_status 
               WHERE vehicle_id = ? ORDER BY ticket_number LIMIT ? OFFSET ?""",
            (vehicle_id, per_page, offset)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_available_count(vehicle_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM ticket_status WHERE vehicle_id = ? AND is_available = 1",
            (vehicle_id,)
        )
        return (await cursor.fetchone())[0]


async def get_banks():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM banks ORDER BY id")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_vehicle(vehicle_id: int, data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        fields = []
        values = []
        for key in ["name", "name_am", "name_or", "subtitle", "price", "total_tickets", "image", "is_active"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(vehicle_id)
            await db.execute(f"UPDATE vehicles SET {', '.join(fields)} WHERE id = ?", values)
            await db.commit()


async def update_banks(banks: list):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM banks")
        for b in banks:
            await db.execute(
                "INSERT INTO banks (name, account, holder) VALUES (?, ?, ?)",
                (b["name"], b["account"], b.get("holder", ""))
            )
        await db.commit()


async def create_order(user_id: int, vehicle_id: int, tickets: list, total: int, full_name: str, phone: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO orders (user_id, vehicle_id, tickets, total_amount, full_name, phone)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, vehicle_id, json.dumps(tickets), total, full_name, phone)
        )
        # Mark tickets as unavailable
        for t in tickets:
            await db.execute(
                "UPDATE ticket_status SET is_available = 0 WHERE vehicle_id = ? AND ticket_number = ?",
                (vehicle_id, t)
            )
        await db.execute(
            "UPDATE vehicles SET sold_tickets = sold_tickets + ? WHERE id = ?",
            (len(tickets), vehicle_id)
        )
        await db.commit()