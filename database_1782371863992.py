import sqlite3
from typing import Optional, List, Dict

DB_PATH = "ww2bot.db"


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._migrate()

    # ── Schema ──────────────────────────────────────────────────
    def _create_tables(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      INTEGER PRIMARY KEY,
                username     TEXT,
                is_admin     INTEGER DEFAULT 0,
                vip_approved INTEGER DEFAULT 0,
                joined_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS players (
                user_id      INTEGER PRIMARY KEY,
                country      TEXT,
                budget       INTEGER DEFAULT 0,
                daily_income INTEGER DEFAULT 0,
                satisfaction INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS player_settings (
                user_id           INTEGER PRIMARY KEY,
                anti_spy_strategy TEXT
            );

            CREATE TABLE IF NOT EXISTS infrastructure (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id TEXT,
                count   INTEGER DEFAULT 1,
                UNIQUE(user_id, item_id)
            );

            CREATE TABLE IF NOT EXISTS military (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id TEXT,
                count   INTEGER DEFAULT 0,
                UNIQUE(user_id, item_id)
            );

            CREATE TABLE IF NOT EXISTS infantry (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id TEXT,
                count   INTEGER DEFAULT 0,
                UNIQUE(user_id, item_id)
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS wars (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                attacker_id       INTEGER,
                defender_id       INTEGER,
                attacker_strategy TEXT,
                defender_strategy TEXT,
                status            TEXT DEFAULT 'pending_defense',
                winner_side       TEXT,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS war_allies (
                war_id    INTEGER,
                ally_id   INTEGER,
                side      TEXT,
                strategy  TEXT,
                PRIMARY KEY(war_id, ally_id)
            );

            CREATE TABLE IF NOT EXISTS ally_requests (
                war_id     INTEGER,
                requester  INTEGER,
                target     INTEGER,
                answered   INTEGER DEFAULT 0,
                PRIMARY KEY(war_id, target)
            );

            CREATE TABLE IF NOT EXISTS friendships (
                user_id   INTEGER,
                friend_id INTEGER,
                PRIMARY KEY(user_id, friend_id)
            );

            CREATE TABLE IF NOT EXISTS alliances (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT UNIQUE,
                leader_id   INTEGER,
                max_members INTEGER DEFAULT 5,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS alliance_members (
                alliance_id INTEGER,
                user_id     INTEGER,
                PRIMARY KEY(alliance_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS spy_missions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                attacker_id INTEGER,
                defender_id INTEGER,
                squads_used INTEGER,
                status      TEXT DEFAULT 'pending_result',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bot_config (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        self.conn.commit()

    def _migrate(self):
        """اضافه کردن ستون‌های جدید به جداول قدیمی"""
        migrations = [
            "ALTER TABLE wars ADD COLUMN winner_side TEXT",
        ]
        for sql in migrations:
            try:
                self.conn.execute(sql)
                self.conn.commit()
            except Exception:
                pass

    # ── Config ───────────────────────────────────────────────────
    def get_config(self, key: str, default: str = "") -> str:
        row = self.conn.execute(
            "SELECT value FROM bot_config WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_config(self, key: str, value: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO bot_config (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()

    # ── Users ────────────────────────────────────────────────────
    def add_user(self, user_id: int, username: str):
        self.conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO players (user_id, budget) VALUES (?, 0)",
            (user_id,)
        )
        self.conn.commit()

    def get_player(self, user_id: int) -> Optional[Dict]:
        row = self.conn.execute(
            """SELECT u.user_id, u.username, u.vip_approved, u.joined_at,
                      p.country, p.budget, p.daily_income, p.satisfaction
               FROM users u JOIN players p ON u.user_id=p.user_id
               WHERE u.user_id=?""",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_player_by_username(self, username: str) -> Optional[Dict]:
        username = username.lstrip("@")
        row = self.conn.execute(
            """SELECT u.user_id, u.username, u.vip_approved,
                      p.country, p.budget, p.daily_income, p.satisfaction
               FROM users u JOIN players p ON u.user_id=p.user_id
               WHERE LOWER(u.username)=LOWER(?)""",
            (username,)
        ).fetchone()
        return dict(row) if row else None

    def get_player_by_country(self, country_code: str) -> Optional[Dict]:
        row = self.conn.execute(
            """SELECT u.user_id, u.username, u.vip_approved,
                      p.country, p.budget, p.daily_income, p.satisfaction
               FROM users u JOIN players p ON u.user_id=p.user_id
               WHERE p.country=?""",
            (country_code,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_users(self) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT user_id, username, joined_at FROM users ORDER BY joined_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def set_vip_approved(self, user_id: int, approved: bool):
        self.conn.execute(
            "UPDATE users SET vip_approved=? WHERE user_id=?",
            (1 if approved else 0, user_id)
        )
        self.conn.commit()

    def is_vip_approved(self, user_id: int) -> bool:
        row = self.conn.execute(
            "SELECT vip_approved FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        return bool(row and row["vip_approved"])

    def get_days_since_joined(self, user_id: int) -> int:
        row = self.conn.execute(
            "SELECT julianday('now') - julianday(joined_at) AS days FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()
        return int(row["days"]) if row else 0

    def kick_player(self, user_id: int):
        """حذف کامل بازیکن از بازی (کشور و تجهیزات)"""
        self.conn.executescript(f"""
            UPDATE players SET country=NULL, budget=0, daily_income=0, satisfaction=0
            WHERE user_id={user_id};
            DELETE FROM infrastructure WHERE user_id={user_id};
            DELETE FROM military WHERE user_id={user_id};
            DELETE FROM infantry WHERE user_id={user_id};
            DELETE FROM player_settings WHERE user_id={user_id};
        """)
        self.conn.commit()

    # ── Country ──────────────────────────────────────────────────
    def set_player_country(self, user_id: int, country: str, budget: int):
        self.conn.execute(
            "UPDATE players SET country=?, budget=? WHERE user_id=?",
            (country, budget, user_id)
        )
        self.conn.commit()

    def get_taken_countries(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT country FROM players WHERE country IS NOT NULL"
        ).fetchall()
        return [r["country"] for r in rows]

    # ── Budget ───────────────────────────────────────────────────
    def update_budget(self, user_id: int, new_budget: int):
        self.conn.execute(
            "UPDATE players SET budget=? WHERE user_id=?",
            (new_budget, user_id)
        )
        self.conn.commit()

    def add_budget(self, user_id: int, amount: int):
        self.conn.execute(
            "UPDATE players SET budget=MIN(budget+?, 9999999999) WHERE user_id=?",
            (amount, user_id)
        )
        self.conn.commit()

    def set_daily_income(self, user_id: int, amount: int):
        self.conn.execute(
            "UPDATE players SET daily_income=? WHERE user_id=?",
            (amount, user_id)
        )
        self.conn.commit()

    def transfer_money(self, from_id: int, to_id: int, amount: int):
        p_from = self.get_player(from_id)
        p_to   = self.get_player(to_id)
        self.conn.execute(
            "UPDATE players SET budget=? WHERE user_id=?",
            (p_from["budget"] - amount, from_id)
        )
        self.conn.execute(
            "UPDATE players SET budget=? WHERE user_id=?",
            (p_to["budget"] + amount, to_id)
        )
        self.conn.commit()

    # ── Infrastructure ───────────────────────────────────────────
    def get_infra_count(self, user_id: int, item_id: str) -> int:
        row = self.conn.execute(
            "SELECT count FROM infrastructure WHERE user_id=? AND item_id=?",
            (user_id, item_id)
        ).fetchone()
        return row["count"] if row else 0

    def buy_infra(self, user_id: int, item_id: str, cost: int, income: int, satisfaction: int):
        self.conn.execute(
            """INSERT INTO infrastructure (user_id, item_id, count) VALUES (?, ?, 1)
               ON CONFLICT(user_id, item_id) DO UPDATE SET count=count+1""",
            (user_id, item_id)
        )
        self.conn.execute(
            """UPDATE players
               SET budget=budget-?,
                   daily_income=MIN(daily_income+?, 9999999999),
                   satisfaction=MIN(satisfaction+?, 100)
               WHERE user_id=?""",
            (cost, income, satisfaction, user_id)
        )
        self.conn.commit()

    # ── Military equipment ───────────────────────────────────────
    def get_equip_count(self, user_id: int, item_id: str) -> int:
        row = self.conn.execute(
            "SELECT count FROM military WHERE user_id=? AND item_id=?",
            (user_id, item_id)
        ).fetchone()
        return row["count"] if row else 0

    def buy_equipment(self, user_id: int, item_id: str, cost: int):
        self.conn.execute(
            """INSERT INTO military (user_id, item_id, count) VALUES (?, ?, 1)
               ON CONFLICT(user_id, item_id) DO UPDATE SET count=count+1""",
            (user_id, item_id)
        )
        self.conn.execute(
            "UPDATE players SET budget=budget-? WHERE user_id=?",
            (cost, user_id)
        )
        self.conn.commit()

    def set_equip_count(self, user_id: int, item_id: str, count: int):
        if count <= 0:
            self.conn.execute(
                "DELETE FROM military WHERE user_id=? AND item_id=?",
                (user_id, item_id)
            )
        else:
            self.conn.execute(
                """INSERT INTO military (user_id, item_id, count) VALUES (?, ?, ?)
                   ON CONFLICT(user_id, item_id) DO UPDATE SET count=?""",
                (user_id, item_id, count, count)
            )
        self.conn.commit()

    def add_equip(self, user_id: int, item_id: str, amount: int):
        self.conn.execute(
            """INSERT INTO military (user_id, item_id, count) VALUES (?, ?, ?)
               ON CONFLICT(user_id, item_id) DO UPDATE SET count=count+?""",
            (user_id, item_id, amount, amount)
        )
        self.conn.commit()

    def get_all_military(self, user_id: int) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT item_id, count FROM military WHERE user_id=? AND count > 0",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def transfer_equipment(self, from_id: int, to_id: int, item_id: str, amount: int):
        self.conn.execute(
            "UPDATE military SET count=count-? WHERE user_id=? AND item_id=?",
            (amount, from_id, item_id)
        )
        self.conn.execute(
            """INSERT INTO military (user_id, item_id, count) VALUES (?, ?, ?)
               ON CONFLICT(user_id, item_id) DO UPDATE SET count=count+?""",
            (to_id, item_id, amount, amount)
        )
        self.conn.commit()

    # ── Infantry ─────────────────────────────────────────────────
    def get_infantry_count(self, user_id: int, item_id: str) -> int:
        row = self.conn.execute(
            "SELECT count FROM infantry WHERE user_id=? AND item_id=?",
            (user_id, item_id)
        ).fetchone()
        return row["count"] if row else 0

    def buy_infantry(self, user_id: int, item_id: str, cost: int):
        self.conn.execute(
            """INSERT INTO infantry (user_id, item_id, count) VALUES (?, ?, 1)
               ON CONFLICT(user_id, item_id) DO UPDATE SET count=count+1""",
            (user_id, item_id)
        )
        self.conn.execute(
            "UPDATE players SET budget=budget-? WHERE user_id=?",
            (cost, user_id)
        )
        self.conn.commit()

    def set_infantry_count(self, user_id: int, item_id: str, count: int):
        if count <= 0:
            self.conn.execute(
                "DELETE FROM infantry WHERE user_id=? AND item_id=?",
                (user_id, item_id)
            )
        else:
            self.conn.execute(
                """INSERT INTO infantry (user_id, item_id, count) VALUES (?, ?, ?)
                   ON CONFLICT(user_id, item_id) DO UPDATE SET count=?""",
                (user_id, item_id, count, count)
            )
        self.conn.commit()

    # ── Full inventory ───────────────────────────────────────────
    def get_full_inventory(self, user_id: int) -> Dict:
        result = {}
        from data import INFRASTRUCTURE, EQUIPMENT, INFANTRY, MISSILES, AIR_DEFENSE
        for item_id, item in INFRASTRUCTURE.items():
            count = self.get_infra_count(user_id, item_id)
            if count > 0:
                result[item["name"]] = count
        for item_id, item in {**EQUIPMENT, **MISSILES, **AIR_DEFENSE}.items():
            count = self.get_equip_count(user_id, item_id)
            if count > 0:
                result[item["name"]] = count
        for item_id, item in INFANTRY.items():
            count = self.get_infantry_count(user_id, item_id)
            if count > 0:
                result[item["name"]] = count
        return result

    def get_military_inventory_text(self, user_id: int) -> str:
        from data import EQUIPMENT, INFANTRY, MISSILES, AIR_DEFENSE
        lines = []
        for item_id, item in {**EQUIPMENT, **MISSILES, **AIR_DEFENSE}.items():
            count = self.get_equip_count(user_id, item_id)
            if count > 0:
                lines.append(f"  • {item['name']}: {count} عدد")
        for item_id, item in INFANTRY.items():
            count = self.get_infantry_count(user_id, item_id)
            if count > 0:
                lines.append(f"  • {item['name']}: {count} جوخه")
        return "\n".join(lines) if lines else "  ❌ بدون تجهیزات"

    def get_military_power(self, user_id: int) -> int:
        """ارزش کل تجهیزات نظامی"""
        from data import EQUIPMENT, MISSILES, AIR_DEFENSE, INFANTRY
        total = 0
        for item_id, item in {**EQUIPMENT, **MISSILES, **AIR_DEFENSE}.items():
            count = self.get_equip_count(user_id, item_id)
            total += count * item["cost"]
        for item_id, item in INFANTRY.items():
            count = self.get_infantry_count(user_id, item_id)
            total += count * item["cost"]
        return total

    # ── Admin ────────────────────────────────────────────────────
    def is_admin(self, user_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM admins WHERE user_id=?", (user_id,)
        ).fetchone()
        return bool(row)

    def add_admin(self, user_id: int):
        self.conn.execute(
            "INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,)
        )
        self.conn.commit()

    def get_all_admins(self) -> List[int]:
        from config import ADMIN_IDS
        rows = self.conn.execute("SELECT user_id FROM admins").fetchall()
        admin_set = set(ADMIN_IDS) | {r["user_id"] for r in rows}
        return list(admin_set)

    def admin_gift_equip(self, user_id: int, item_id: str, amount: int):
        self.conn.execute(
            """INSERT INTO military (user_id, item_id, count) VALUES (?, ?, ?)
               ON CONFLICT(user_id, item_id) DO UPDATE SET count=count+?""",
            (user_id, item_id, amount, amount)
        )
        self.conn.commit()

    def admin_gift_money(self, user_id: int, amount: int):
        self.conn.execute(
            "UPDATE players SET budget=MIN(budget+?, 9999999999) WHERE user_id=?",
            (amount, user_id)
        )
        self.conn.commit()

    # ── Season reset ─────────────────────────────────────────────
    def reset_season(self):
        self.conn.executescript("""
            UPDATE players SET country=NULL, budget=0, daily_income=0, satisfaction=0;
            DELETE FROM infrastructure;
            DELETE FROM military;
            DELETE FROM infantry;
            DELETE FROM wars;
            DELETE FROM war_allies;
            DELETE FROM ally_requests;
            DELETE FROM alliances;
            DELETE FROM alliance_members;
            DELETE FROM spy_missions;
            DELETE FROM player_settings;
        """)
        self.conn.commit()

    # ── All players ──────────────────────────────────────────────
    def get_all_players(self) -> List[Dict]:
        rows = self.conn.execute(
            """SELECT u.user_id, u.username, p.country, p.budget,
                      p.daily_income, p.satisfaction
               FROM users u JOIN players p ON u.user_id=p.user_id
               WHERE p.country IS NOT NULL"""
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Wars ─────────────────────────────────────────────────────
    def create_war(self, attacker_id: int, defender_id: int, strategy: str) -> int:
        cur = self.conn.execute(
            """INSERT INTO wars (attacker_id, defender_id, attacker_strategy, status)
               VALUES (?, ?, ?, 'pending_defense')""",
            (attacker_id, defender_id, strategy)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_war(self, war_id: int) -> Optional[Dict]:
        row = self.conn.execute(
            "SELECT * FROM wars WHERE id=?", (war_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_active_war_for_defender(self, defender_id: int) -> Optional[Dict]:
        row = self.conn.execute(
            "SELECT * FROM wars WHERE defender_id=? AND status='pending_defense'",
            (defender_id,)
        ).fetchone()
        return dict(row) if row else None

    def set_defender_strategy(self, war_id: int, strategy: str):
        self.conn.execute(
            "UPDATE wars SET defender_strategy=?, status='pending_allies' WHERE id=?",
            (strategy, war_id)
        )
        self.conn.commit()

    def set_war_status(self, war_id: int, status: str):
        self.conn.execute(
            "UPDATE wars SET status=? WHERE id=?", (status, war_id)
        )
        self.conn.commit()

    def set_war_winner(self, war_id: int, winner_side: str):
        self.conn.execute(
            "UPDATE wars SET winner_side=?, status='analyzed' WHERE id=?",
            (winner_side, war_id)
        )
        self.conn.commit()

    def get_all_active_wars(self) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM wars WHERE status NOT IN ('analyzed') ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_analyzed_wars(self, limit: int = 20) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM wars WHERE status='analyzed' ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_pending_defense_wars_older_than(self, hours: int) -> List[Dict]:
        rows = self.conn.execute(
            """SELECT * FROM wars WHERE status='pending_defense'
               AND (julianday('now') - julianday(created_at)) * 24 >= ?""",
            (hours,)
        ).fetchall()
        return [dict(r) for r in rows]

    def apply_war_loot(self, winner_id: int, loser_id: int, loot_pct: int):
        """برنده درصدی از تجهیزات بازنده را می‌گیرد"""
        from data import EQUIPMENT, MISSILES, AIR_DEFENSE, INFANTRY
        all_mil = {**EQUIPMENT, **MISSILES, **AIR_DEFENSE}

        for item_id in all_mil:
            loser_count = self.get_equip_count(loser_id, item_id)
            if loser_count > 0:
                loot = max(1, int(loser_count * loot_pct / 100))
                loot = min(loot, loser_count)
                new_loser = loser_count - loot
                self.set_equip_count(loser_id, item_id, new_loser)
                self.add_equip(winner_id, item_id, loot)

        for item_id in INFANTRY:
            loser_count = self.get_infantry_count(loser_id, item_id)
            if loser_count > 0:
                loot = max(1, int(loser_count * loot_pct / 100))
                loot = min(loot, loser_count)
                new_loser = loser_count - loot
                self.set_infantry_count(loser_id, item_id, new_loser)
                self.conn.execute(
                    """INSERT INTO infantry (user_id, item_id, count) VALUES (?, ?, ?)
                       ON CONFLICT(user_id, item_id) DO UPDATE SET count=count+?""",
                    (winner_id, item_id, loot, loot)
                )
        self.conn.commit()

    def add_war_ally(self, war_id: int, ally_id: int, side: str, strategy: str):
        self.conn.execute(
            """INSERT OR REPLACE INTO war_allies (war_id, ally_id, side, strategy)
               VALUES (?, ?, ?, ?)""",
            (war_id, ally_id, side, strategy)
        )
        self.conn.commit()

    def get_war_allies(self, war_id: int) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM war_allies WHERE war_id=?", (war_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def add_ally_request(self, war_id: int, requester_id: int, target_id: int):
        self.conn.execute(
            """INSERT OR IGNORE INTO ally_requests (war_id, requester, target)
               VALUES (?, ?, ?)""",
            (war_id, requester_id, target_id)
        )
        self.conn.commit()

    def get_pending_ally_requests(self, war_id: int) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM ally_requests WHERE war_id=? AND answered=0",
            (war_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def answer_ally_request(self, war_id: int, target_id: int):
        self.conn.execute(
            "UPDATE ally_requests SET answered=1 WHERE war_id=? AND target=?",
            (war_id, target_id)
        )
        self.conn.commit()

    # ── Friendships ──────────────────────────────────────────────
    def add_friend(self, user_id: int, friend_id: int):
        self.conn.execute(
            "INSERT OR IGNORE INTO friendships (user_id, friend_id) VALUES (?, ?)",
            (user_id, friend_id)
        )
        self.conn.commit()

    def remove_friend(self, user_id: int, friend_id: int):
        self.conn.execute(
            "DELETE FROM friendships WHERE user_id=? AND friend_id=?",
            (user_id, friend_id)
        )
        self.conn.commit()

    def get_friends(self, user_id: int) -> List[int]:
        rows = self.conn.execute(
            "SELECT friend_id FROM friendships WHERE user_id=?", (user_id,)
        ).fetchall()
        return [r["friend_id"] for r in rows]

    # ── Alliances ────────────────────────────────────────────────
    def create_alliance(self, name: str, leader_id: int) -> int:
        cur = self.conn.execute(
            "INSERT INTO alliances (name, leader_id) VALUES (?, ?)",
            (name, leader_id)
        )
        alliance_id = cur.lastrowid
        self.conn.execute(
            "INSERT OR IGNORE INTO alliance_members (alliance_id, user_id) VALUES (?, ?)",
            (alliance_id, leader_id)
        )
        self.conn.commit()
        return alliance_id

    def get_alliance(self, alliance_id: int) -> Optional[Dict]:
        row = self.conn.execute(
            "SELECT * FROM alliances WHERE id=?", (alliance_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_alliance_by_name(self, name: str) -> Optional[Dict]:
        row = self.conn.execute(
            "SELECT * FROM alliances WHERE LOWER(name)=LOWER(?)", (name,)
        ).fetchone()
        return dict(row) if row else None

    def get_player_alliance(self, user_id: int) -> Optional[Dict]:
        row = self.conn.execute(
            """SELECT a.* FROM alliances a
               JOIN alliance_members am ON a.id=am.alliance_id
               WHERE am.user_id=?""",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_alliance_members(self, alliance_id: int) -> List[int]:
        rows = self.conn.execute(
            "SELECT user_id FROM alliance_members WHERE alliance_id=?",
            (alliance_id,)
        ).fetchall()
        return [r["user_id"] for r in rows]

    def get_all_alliances(self) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM alliances ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def join_alliance(self, alliance_id: int, user_id: int):
        self.conn.execute(
            "INSERT OR IGNORE INTO alliance_members (alliance_id, user_id) VALUES (?, ?)",
            (alliance_id, user_id)
        )
        self.conn.commit()

    def leave_alliance(self, user_id: int):
        alliance = self.get_player_alliance(user_id)
        if not alliance:
            return
        self.conn.execute(
            "DELETE FROM alliance_members WHERE alliance_id=? AND user_id=?",
            (alliance["id"], user_id)
        )
        if alliance["leader_id"] == user_id:
            members = self.get_alliance_members(alliance["id"])
            remaining = [m for m in members if m != user_id]
            if remaining:
                self.conn.execute(
                    "UPDATE alliances SET leader_id=? WHERE id=?",
                    (remaining[0], alliance["id"])
                )
            else:
                self.conn.execute(
                    "DELETE FROM alliances WHERE id=?", (alliance["id"],)
                )
                self.conn.execute(
                    "DELETE FROM alliance_members WHERE alliance_id=?", (alliance["id"],)
                )
        self.conn.commit()

    def kick_from_alliance(self, alliance_id: int, user_id: int):
        self.conn.execute(
            "DELETE FROM alliance_members WHERE alliance_id=? AND user_id=?",
            (alliance_id, user_id)
        )
        self.conn.commit()

    def set_alliance_max_members(self, alliance_id: int, max_members: int):
        self.conn.execute(
            "UPDATE alliances SET max_members=? WHERE id=?",
            (max_members, alliance_id)
        )
        self.conn.commit()

    def count_alliance_members(self, alliance_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS cnt FROM alliance_members WHERE alliance_id=?",
            (alliance_id,)
        ).fetchone()
        return row["cnt"] if row else 0

    # ── Spy missions ─────────────────────────────────────────────
    def create_spy_mission(self, attacker_id: int, defender_id: int, squads: int) -> int:
        cur = self.conn.execute(
            """INSERT INTO spy_missions (attacker_id, defender_id, squads_used, status)
               VALUES (?, ?, ?, 'pending_result')""",
            (attacker_id, defender_id, squads)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_spy_mission(self, mission_id: int) -> Optional[Dict]:
        row = self.conn.execute(
            "SELECT * FROM spy_missions WHERE id=?", (mission_id,)
        ).fetchone()
        return dict(row) if row else None

    def set_spy_mission_status(self, mission_id: int, status: str):
        self.conn.execute(
            "UPDATE spy_missions SET status=? WHERE id=?",
            (status, mission_id)
        )
        self.conn.commit()

    def get_pending_spy_missions(self) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM spy_missions WHERE status='pending_result' ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Player settings (anti-spy strategy) ──────────────────────
    def get_anti_spy_strategy(self, user_id: int) -> str:
        row = self.conn.execute(
            "SELECT anti_spy_strategy FROM player_settings WHERE user_id=?",
            (user_id,)
        ).fetchone()
        return row["anti_spy_strategy"] if row and row["anti_spy_strategy"] else ""

    def set_anti_spy_strategy(self, user_id: int, strategy: str):
        self.conn.execute(
            """INSERT INTO player_settings (user_id, anti_spy_strategy)
               VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET anti_spy_strategy=?""",
            (user_id, strategy, strategy)
        )
        self.conn.commit()

    # ── Leaderboard ──────────────────────────────────────────────
    def get_leaderboard_by_budget(self, limit: int = 15) -> List[Dict]:
        rows = self.conn.execute(
            """SELECT u.user_id, u.username, p.country, p.budget,
                      p.daily_income, p.satisfaction
               FROM users u JOIN players p ON u.user_id=p.user_id
               WHERE p.country IS NOT NULL
               ORDER BY p.budget DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_leaderboard_by_satisfaction(self, limit: int = 15) -> List[Dict]:
        rows = self.conn.execute(
            """SELECT u.user_id, u.username, p.country, p.budget,
                      p.daily_income, p.satisfaction
               FROM users u JOIN players p ON u.user_id=p.user_id
               WHERE p.country IS NOT NULL
               ORDER BY p.satisfaction DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
