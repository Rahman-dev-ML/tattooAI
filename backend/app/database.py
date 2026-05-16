"""
SQLite database for device-based credit tracking.
Stores at /data/tattoo.db on Fly.io (persistent volume) or ./tattoo.db locally.
"""
import os
import time
import aiosqlite

_data_dir = "/data"
if os.path.exists(_data_dir):
    DB_PATH = os.environ.get("DB_PATH", "/data/tattoo.db")
else:
    DB_PATH = os.environ.get("DB_PATH", "./tattoo.db")

FREE_CREDITS = 2
CREDITS_PER_PURCHASE = 5


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                credits INTEGER NOT NULL DEFAULT 2,
                ip_address TEXT,
                created_at REAL NOT NULL,
                last_payment_at REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                payfast_transaction_id TEXT,
                basket_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at REAL NOT NULL,
                FOREIGN KEY (device_id) REFERENCES devices(device_id)
            )
        """)
        # Migration: add ip_address column if it doesn't exist yet
        try:
            await db.execute("ALTER TABLE devices ADD COLUMN ip_address TEXT")
            await db.commit()
        except Exception:
            pass  # Column already exists
        await db.commit()
    print(f"[DB] Initialized at {DB_PATH}")


async def _ip_has_depleted_devices(ip: str, exclude_device_id: str) -> bool:
    """Returns True if this IP already has any device with 0 credits (not paid).
    Threshold = 1: first device per IP gets free trial, any subsequent browser/device does not."""
    if not ip:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT COUNT(*) FROM devices
               WHERE ip_address = ? AND device_id != ? AND credits = 0 AND last_payment_at IS NULL""",
            (ip, exclude_device_id)
        )
        row = await cursor.fetchone()
        return (row[0] if row else 0) >= 1


async def get_or_create_device(device_id: str, ip_address: str = "") -> int:
    """Returns current credits. Creates device with FREE_CREDITS if new.
    If the IP has already had 2+ depleted free-trial devices, starts at 0."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT credits FROM devices WHERE device_id = ?", (device_id,))
        row = await cursor.fetchone()
        if row:
            # Update IP if we have one and it wasn't stored before
            if ip_address:
                await db.execute(
                    "UPDATE devices SET ip_address = ? WHERE device_id = ? AND ip_address IS NULL",
                    (ip_address, device_id)
                )
                await db.commit()
            return row[0]

        # New device — check IP to decide starting credits
        starting_credits = FREE_CREDITS
        if ip_address and await _ip_has_depleted_devices(ip_address, device_id):
            starting_credits = 0
            print(f"[DB] IP {ip_address} already has depleted devices — new device starts at 0")

        await db.execute(
            "INSERT INTO devices (device_id, credits, ip_address, created_at) VALUES (?, ?, ?, ?)",
            (device_id, starting_credits, ip_address or None, time.time())
        )
        await db.commit()
        return starting_credits


async def deduct_credit(device_id: str, ip_address: str = "") -> int:
    """Deducts 1 credit. Returns remaining credits, or -1 if insufficient."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT credits FROM devices WHERE device_id = ?", (device_id,))
        row = await cursor.fetchone()
        if not row:
            # New device seen at deduct time — apply same IP check
            starting_credits = FREE_CREDITS
            if ip_address and await _ip_has_depleted_devices(ip_address, device_id):
                starting_credits = 0
            await db.execute(
                "INSERT INTO devices (device_id, credits, ip_address, created_at) VALUES (?, ?, ?, ?)",
                (device_id, starting_credits, ip_address or None, time.time())
            )
            await db.commit()
            row = (starting_credits,)

        current = row[0]
        if current <= 0:
            return -1

        new_credits = current - 1
        await db.execute("UPDATE devices SET credits = ? WHERE device_id = ?", (new_credits, device_id))
        await db.commit()
        return new_credits


async def add_credits(device_id: str, amount: int = CREDITS_PER_PURCHASE) -> int:
    """Adds credits after successful payment. Returns new total."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT credits FROM devices WHERE device_id = ?", (device_id,))
        row = await cursor.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO devices (device_id, credits, created_at, last_payment_at) VALUES (?, ?, ?, ?)",
                (device_id, amount, time.time(), time.time())
            )
            await db.commit()
            return amount

        new_credits = row[0] + amount
        await db.execute(
            "UPDATE devices SET credits = ?, last_payment_at = ? WHERE device_id = ?",
            (new_credits, time.time(), device_id)
        )
        await db.commit()
        return new_credits


async def create_transaction(device_id: str, basket_id: str, amount: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO transactions (device_id, basket_id, amount, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
            (device_id, basket_id, amount, time.time())
        )
        await db.commit()
        return cursor.lastrowid or 0


async def update_transaction(basket_id: str, payfast_txn_id: str, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE transactions SET payfast_transaction_id = ?, status = ? WHERE basket_id = ?",
            (payfast_txn_id, status, basket_id)
        )
        await db.commit()


async def get_device_id_by_basket(basket_id: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT device_id FROM transactions WHERE basket_id = ?", (basket_id,))
        row = await cursor.fetchone()
        return row[0] if row else None
