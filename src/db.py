import csv
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from src.paths import backup_dir, db_path


def get_conn():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS brands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """
    )
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY(brand_id) REFERENCES brands(id)
    )
    """
    )
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS sizes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY(model_id) REFERENCES models(id)
    )
    """
    )
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """
    )
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS barcodes (
        serial TEXT PRIMARY KEY,
        size_id INTEGER NOT NULL,
        FOREIGN KEY(size_id) REFERENCES sizes(id) ON DELETE CASCADE
    )
    """
    )
    conn.commit()

    # Seed minimal data if empty
    cur.execute("SELECT COUNT(1) FROM brands")
    if cur.fetchone()[0] == 0:
        seed(conn)

    conn.close()


def seed(conn):
    cur = conn.cursor()
    brands = ["Engels", "Schildermans", "Mergaerts", "VDBIEST"]
    models = {
        "Engels": ["Cyriel"],
        "Schildermans": ["Lode"],
        "Mergaerts": ["Anton", "Lennard"],
        "VDBIEST": ["Bram"],
    }
    sizes = {
        "Cyriel": ["175cm"],
        "Lode": ["172cm"],
        "Anton": ["185cm"],
        "Lennard": ["215cm"],
        "Bram": ["57cm"],
    }

    for b in brands:
        cur.execute("INSERT INTO brands (name) VALUES (?)", (b,))
        bid = cur.lastrowid
        for m in models[b]:
            cur.execute("INSERT INTO models (brand_id, name) VALUES (?,?)", (bid, m))
            mid = cur.lastrowid
            for s in sizes.get(m, []):
                cur.execute("INSERT INTO sizes (model_id, name) VALUES (?,?)", (mid, s))

    conn.commit()


def get_brands():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM brands ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_models(brand_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name FROM models WHERE brand_id = ? ORDER BY name", (brand_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_sizes(model_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name FROM sizes WHERE model_id = ? ORDER BY name", (model_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_catalog_entries() -> list[dict[str, str]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.name, m.name, s.name
        FROM sizes s
        JOIN models m ON m.id = s.model_id
        JOIN brands b ON b.id = m.brand_id
        ORDER BY b.name, m.name, s.name
    """
    )
    rows = [
        {"brand": brand, "model": model, "size": size}
        for brand, model, size in cur.fetchall()
    ]
    conn.close()
    return rows


def set_printer_settings(settings: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "REPLACE INTO settings (key, value) VALUES (?,?)",
        ("printer", json.dumps(settings)),
    )
    conn.commit()
    conn.close()


def get_printer_settings():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", ("printer",))
    row = cur.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return {}
    return {}


def add_brand(name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO brands (name) VALUES (?)", (name.strip(),))
    conn.commit()
    brand_id = cur.lastrowid
    conn.close()
    return brand_id


def rename_brand(brand_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE brands SET name = ? WHERE id = ?", (name.strip(), brand_id))
    conn.commit()
    conn.close()


def delete_brand(brand_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM models WHERE brand_id = ?", (brand_id,))
    model_ids = [row[0] for row in cur.fetchall()]
    for model_id in model_ids:
        cur.execute("DELETE FROM sizes WHERE model_id = ?", (model_id,))
    cur.execute("DELETE FROM models WHERE brand_id = ?", (brand_id,))
    cur.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
    conn.commit()
    conn.close()


def add_model(brand_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO models (brand_id, name) VALUES (?, ?)", (brand_id, name.strip())
    )
    conn.commit()
    model_id = cur.lastrowid
    conn.close()
    return model_id


def rename_model(model_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE models SET name = ? WHERE id = ?", (name.strip(), model_id))
    conn.commit()
    conn.close()


def delete_model(model_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM sizes WHERE model_id = ?", (model_id,))
    cur.execute("DELETE FROM models WHERE id = ?", (model_id,))
    conn.commit()
    conn.close()


def add_size(model_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sizes (model_id, name) VALUES (?, ?)", (model_id, name.strip())
    )
    conn.commit()
    size_id = cur.lastrowid
    conn.close()
    return size_id


def rename_size(size_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE sizes SET name = ? WHERE id = ?", (name.strip(), size_id))
    conn.commit()
    conn.close()


def delete_size(size_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM sizes WHERE id = ?", (size_id,))
    conn.commit()
    conn.close()


def backup_database():
    target_dir = backup_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = target_dir / f"labelmate-{timestamp}.db"
    source = db_path()
    if source.exists():
        shutil.copy2(source, backup_path)
    return backup_path


def reset_catalog():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM barcodes")
    cur.execute("DELETE FROM sizes")
    cur.execute("DELETE FROM models")
    cur.execute("DELETE FROM brands")
    conn.commit()
    seed(conn)
    conn.close()


def _normalize_serial(value: str) -> str:
    return value.strip()


def _split_serials(cell: str) -> list[str]:
    if not cell or not cell.strip():
        return []
    serials: list[str] = []
    for chunk in cell.replace(";", ",").split(","):
        serial = _normalize_serial(chunk)
        if serial:
            serials.append(serial)
    return serials


def _csv_column(columns: dict[str, int], exact: str, *keywords: str) -> int | None:
    if exact in columns:
        return columns[exact]
    for name, index in columns.items():
        if any(keyword in name for keyword in keywords):
            return index
    return None


def _detect_csv_delimiter(sample: str) -> str:
    if sample.count(";") >= sample.count(","):
        return ";"
    return ","


def _parse_catalog_csv(path: Path | str) -> list[tuple[str, str, str, list[str]]]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        delimiter = _detect_csv_delimiter(sample.splitlines()[0] if sample else ",")
        reader = csv.reader(handle, delimiter=delimiter)
        header = next(reader, None)
        if not header:
            raise ValueError("CSV file is empty.")
        columns = {name.strip().lower(): index for index, name in enumerate(header)}

        brand_col = _csv_column(columns, "brand", "brand")
        model_col = _csv_column(columns, "model", "model")
        size_col = _csv_column(columns, "size", "size")
        serial_col = _csv_column(columns, "serial", "barcode", "qr", "rfid")

        missing = []
        if brand_col is None:
            missing.append("brand")
        if model_col is None:
            missing.append("model")
        if size_col is None:
            missing.append("size")
        if missing:
            raise ValueError(
                f'CSV must include columns: brand, model, size (missing: {", ".join(missing)})'
            )

        rows: list[tuple[str, str, str, list[str]]] = []
        for line_no, record in enumerate(reader, start=2):
            if not record or not any(cell.strip() for cell in record):
                continue
            try:
                brand = record[brand_col].strip()
                model = record[model_col].strip()
                size = record[size_col].strip()
                serial_cell = record[serial_col].strip() if serial_col is not None else ""
            except IndexError as exc:
                raise ValueError(f"CSV row {line_no} is incomplete.") from exc
            if not brand or not model or not size:
                raise ValueError(f"CSV row {line_no} must have brand, model, and size.")
            rows.append((brand, model, size, _split_serials(serial_cell)))
    if not rows:
        raise ValueError("CSV file has a header but no data rows.")
    return rows


def lookup_by_barcode(serial: str) -> dict[str, str] | None:
    serial = _normalize_serial(serial)
    if not serial:
        return None
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.name, m.name, s.name
        FROM barcodes bc
        JOIN sizes s ON s.id = bc.size_id
        JOIN models m ON m.id = s.model_id
        JOIN brands b ON b.id = m.brand_id
        WHERE bc.serial = ?
        """,
        (serial,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"brand": row[0], "model": row[1], "size": row[2]}


def export_catalog_csv(path: Path | str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            GROUP_CONCAT(bc.serial, ',') AS serials,
            b.name,
            m.name,
            s.name
        FROM sizes s
        JOIN models m ON m.id = s.model_id
        JOIN brands b ON b.id = m.brand_id
        LEFT JOIN barcodes bc ON bc.size_id = s.id
        GROUP BY s.id
        ORDER BY b.name, m.name, s.name
        """
    )
    rows = cur.fetchall()
    conn.close()

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["QR codes / RFID serial numbers", "Brand", "Model", "Size"])
        for serials, brand, model, size in rows:
            writer.writerow([serials or "", brand, model, size])
    return len(rows)


def _get_or_create_size_id(
    cur: sqlite3.Cursor,
    brand_ids: dict[str, int],
    model_ids: dict[tuple[int, str], int],
    brand: str,
    model: str,
    size: str,
) -> tuple[int, bool]:
    if brand not in brand_ids:
        cur.execute("SELECT id FROM brands WHERE name = ?", (brand,))
        found = cur.fetchone()
        if found:
            brand_ids[brand] = found[0]
        else:
            cur.execute("INSERT INTO brands (name) VALUES (?)", (brand,))
            brand_ids[brand] = cur.lastrowid

    brand_id = brand_ids[brand]
    model_key = (brand_id, model)
    if model_key not in model_ids:
        cur.execute(
            "SELECT id FROM models WHERE brand_id = ? AND name = ?",
            (brand_id, model),
        )
        found = cur.fetchone()
        if found:
            model_ids[model_key] = found[0]
        else:
            cur.execute(
                "INSERT INTO models (brand_id, name) VALUES (?, ?)",
                (brand_id, model),
            )
            model_ids[model_key] = cur.lastrowid

    model_id = model_ids[model_key]
    cur.execute(
        "SELECT id FROM sizes WHERE model_id = ? AND name = ?",
        (model_id, size),
    )
    found = cur.fetchone()
    if found:
        return found[0], False

    cur.execute(
        "INSERT INTO sizes (model_id, name) VALUES (?, ?)",
        (model_id, size),
    )
    return cur.lastrowid, True


def import_catalog_csv(path: Path | str, *, replace: bool = True) -> dict:
    rows = _parse_catalog_csv(path)
    conn = get_conn()
    cur = conn.cursor()
    try:
        if replace:
            cur.execute("DELETE FROM barcodes")
            cur.execute("DELETE FROM sizes")
            cur.execute("DELETE FROM models")
            cur.execute("DELETE FROM brands")

        brand_ids: dict[str, int] = {}
        model_ids: dict[tuple[int, str], int] = {}
        sizes_added = 0
        barcodes_added = 0

        for brand, model, size, serials in rows:
            size_id, created = _get_or_create_size_id(
                cur, brand_ids, model_ids, brand, model, size
            )
            if created:
                sizes_added += 1

            for serial in serials:
                cur.execute(
                    "INSERT OR REPLACE INTO barcodes (serial, size_id) VALUES (?, ?)",
                    (serial, size_id),
                )
                barcodes_added += 1

        conn.commit()
    finally:
        conn.close()

    return {
        "rows_read": len(rows),
        "sizes_added": sizes_added,
        "barcodes_added": barcodes_added,
        "replaced": replace,
    }
