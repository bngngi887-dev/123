import aiosqlite
import json
from datetime import datetime
import os

DB_PATH = "data/railway.db"

async def init_db():
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL, station_from TEXT NOT NULL, station_to TEXT NOT NULL,
                carrier TEXT NOT NULL, train_number TEXT NOT NULL, host_id TEXT NOT NULL,
                host_name TEXT NOT NULL, times TEXT NOT NULL, stops TEXT NOT NULL,
                wagons TEXT NOT NULL, extra_info TEXT NOT NULL, channel_id INTEGER,
                message_id INTEGER, status TEXT DEFAULT 'scheduled',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, trip_id INTEGER NOT NULL,
                remind_at TEXT NOT NULL, text TEXT NOT NULL, sent INTEGER DEFAULT 0,
                FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
            )
        """)
        await db.commit()

async def init_staff_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trip_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                trip_id INTEGER NOT NULL,
                driver_id TEXT NOT NULL, 
                role_type TEXT NOT NULL, 
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vacations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, driver_id TEXT NOT NULL,
                start_date TEXT NOT NULL, end_date TEXT NOT NULL,
                reason TEXT, status TEXT DEFAULT 'pending'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS no_shows (
                id INTEGER PRIMARY KEY AUTOINCREMENT, trip_id INTEGER NOT NULL,
                driver_id TEXT NOT NULL, reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_trip(data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO trips (date, station_from, station_to, carrier, train_number,
                               host_id, host_name, times, stops, wagons, extra_info, channel_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["date"], data["station_from"], data["station_to"], data["carrier"],
            data["train_number"], data["host_id"], data["host_name"],
            json.dumps(data["times"], ensure_ascii=False), json.dumps(data["stops"], ensure_ascii=False),
            json.dumps(data["wagons"], ensure_ascii=False), json.dumps(data.get("extra_info", {}), ensure_ascii=False),
            data.get("channel_id")
        ))
        await db.commit()
        return cursor.lastrowid

async def get_trip(trip_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)) as cur:
            row = await cur.fetchone()
            return _row_to_dict(row) if row else None

async def get_active_trips() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM trips WHERE status IN ('scheduled','boarding') ORDER BY date") as cur:
            return [_row_to_dict(r) for r in await cur.fetchall()]

async def set_trip_message(trip_id: int, channel_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE trips SET channel_id = ?, message_id = ? WHERE id = ?", (channel_id, message_id, trip_id))
        await db.commit()

async def add_reminder(trip_id: int, remind_at: str, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO reminders (trip_id, remind_at, text) VALUES (?, ?, ?)", (trip_id, remind_at, text))
        await db.commit()

async def get_pending_reminders() -> list[dict]:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reminders WHERE sent = 0 AND remind_at <= ?", (now,)) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def mark_reminder_sent(reminder_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        await db.commit()

async def add_trip_request(trip_id: int, driver_id: str, role_type: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO trip_requests (trip_id, driver_id, role_type) VALUES (?, ?, ?)", (trip_id, driver_id, role_type))
        await db.commit()
        return cursor.lastrowid

async def update_request_status(req_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE trip_requests SET status = ? WHERE id = ?", (status, req_id))
        await db.commit()

async def add_vacation(driver_id: str, start: str, end: str, reason: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO vacations (driver_id, start_date, end_date, reason) VALUES (?, ?, ?, ?)", (driver_id, start, end, reason))
        await db.commit()

async def add_no_show(trip_id: int, driver_id: str, reason: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO no_shows (trip_id, driver_id, reason) VALUES (?, ?, ?)", (trip_id, driver_id, reason))
        await db.commit()

def _row_to_dict(row) -> dict:
    d = dict(row)
    d["times"] = json.loads(d["times"])
    d["stops"] = json.loads(d["stops"])
    d["wagons"] = json.loads(d["wagons"])
    d["extra_info"] = json.loads(d["extra_info"]) if d["extra_info"] else {}
    return d