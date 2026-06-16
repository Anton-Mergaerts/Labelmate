import sqlite3
import json
import shutil
from datetime import datetime

from src.paths import backup_dir, db_path


def get_conn():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS brands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY(brand_id) REFERENCES brands(id)
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sizes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY(model_id) REFERENCES models(id)
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')
    conn.commit()

    # Seed minimal data if empty
    cur.execute('SELECT COUNT(1) FROM brands')
    if cur.fetchone()[0] == 0:
        seed(conn)

    conn.close()


def seed(conn):
    cur = conn.cursor()
    brands = ['Acme', 'Globex']
    models = {
        'Acme': ['A100', 'A200'],
        'Globex': ['G1', 'G2']
    }
    sizes = {
        'A100': ['Small', 'Medium'],
        'A200': ['Medium', 'Large'],
        'G1': ['One'],
        'G2': ['Two']
    }

    for b in brands:
        cur.execute('INSERT INTO brands (name) VALUES (?)', (b,))
        bid = cur.lastrowid
        for m in models[b]:
            cur.execute('INSERT INTO models (brand_id, name) VALUES (?,?)', (bid, m))
            mid = cur.lastrowid
            for s in sizes.get(m, []):
                cur.execute('INSERT INTO sizes (model_id, name) VALUES (?,?)', (mid, s))

    conn.commit()


def get_brands():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM brands ORDER BY name')
    rows = cur.fetchall()
    conn.close()
    return rows


def get_models(brand_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM models WHERE brand_id = ? ORDER BY name', (brand_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_sizes(model_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM sizes WHERE model_id = ? ORDER BY name', (model_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def set_printer_settings(settings: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('REPLACE INTO settings (key, value) VALUES (?,?)', ('printer', json.dumps(settings)))
    conn.commit()
    conn.close()


def get_printer_settings():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT value FROM settings WHERE key = ?', ('printer',))
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
    cur.execute('INSERT INTO brands (name) VALUES (?)', (name.strip(),))
    conn.commit()
    brand_id = cur.lastrowid
    conn.close()
    return brand_id


def rename_brand(brand_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('UPDATE brands SET name = ? WHERE id = ?', (name.strip(), brand_id))
    conn.commit()
    conn.close()


def delete_brand(brand_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id FROM models WHERE brand_id = ?', (brand_id,))
    model_ids = [row[0] for row in cur.fetchall()]
    for model_id in model_ids:
        cur.execute('DELETE FROM sizes WHERE model_id = ?', (model_id,))
    cur.execute('DELETE FROM models WHERE brand_id = ?', (brand_id,))
    cur.execute('DELETE FROM brands WHERE id = ?', (brand_id,))
    conn.commit()
    conn.close()


def add_model(brand_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('INSERT INTO models (brand_id, name) VALUES (?, ?)', (brand_id, name.strip()))
    conn.commit()
    model_id = cur.lastrowid
    conn.close()
    return model_id


def rename_model(model_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('UPDATE models SET name = ? WHERE id = ?', (name.strip(), model_id))
    conn.commit()
    conn.close()


def delete_model(model_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('DELETE FROM sizes WHERE model_id = ?', (model_id,))
    cur.execute('DELETE FROM models WHERE id = ?', (model_id,))
    conn.commit()
    conn.close()


def add_size(model_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('INSERT INTO sizes (model_id, name) VALUES (?, ?)', (model_id, name.strip()))
    conn.commit()
    size_id = cur.lastrowid
    conn.close()
    return size_id


def rename_size(size_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('UPDATE sizes SET name = ? WHERE id = ?', (name.strip(), size_id))
    conn.commit()
    conn.close()


def delete_size(size_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('DELETE FROM sizes WHERE id = ?', (size_id,))
    conn.commit()
    conn.close()


def backup_database():
    target_dir = backup_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_path = target_dir / f'labelmate-{timestamp}.db'
    source = db_path()
    if source.exists():
        shutil.copy2(source, backup_path)
    return backup_path


def reset_catalog():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('DELETE FROM sizes')
    cur.execute('DELETE FROM models')
    cur.execute('DELETE FROM brands')
    conn.commit()
    seed(conn)
    conn.close()
