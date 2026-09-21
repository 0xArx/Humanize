"""The agent's own memory: notes and people in one local SQLite file. No account, no server.

  add(text, kind, tags)        remember something
  search(query, limit)         find it again (full-text search when SQLite has FTS5, else substring)
  person(name, handle, notes)  add or update someone it has met
  people(limit)                who it knows, most recently updated first

The file is $HUMANIZE_HOME/memory.db (mode 600). `humanize.py self push` backs it up, encrypted,
alongside the identity.
"""
import contextlib
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store  # noqa: E402

SCHEMA = """
create table if not exists memories(id integer primary key, at text not null, kind text not null default 'note', text text not null, tags text not null default '');
create table if not exists people(id integer primary key, name text not null unique, handle text, notes text, met text, updated text);
"""
FTS = """
create virtual table if not exists memories_fts using fts5(text, tags, content='memories', content_rowid='id');
create trigger if not exists memories_ai after insert on memories begin insert into memories_fts(rowid, text, tags) values (new.id, new.text, new.tags); end;
create trigger if not exists memories_ad after delete on memories begin insert into memories_fts(memories_fts, rowid, text, tags) values ('delete', old.id, old.text, old.tags); end;
"""


def db_path():
    return store.home() / "memory.db"


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class DB(sqlite3.Connection):
    has_fts = False


def connect():
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fresh = not p.exists()
    c = sqlite3.connect(str(p), factory=DB)
    c.row_factory = sqlite3.Row
    if fresh:
        os.chmod(p, 0o600)
    c.executescript(SCHEMA)
    try:
        c.executescript(FTS)
        c.has_fts = True
    except sqlite3.OperationalError:
        c.has_fts = False
    return c


@contextlib.contextmanager
def db():
    c = connect()
    try:
        yield c
        c.commit()
    finally:
        c.close()


def add(text, kind="note", tags=""):
    text = (text or "").strip()
    if not text:
        raise ValueError("nothing to remember")
    with db() as c:
        cur = c.execute("insert into memories(at, kind, text, tags) values (?,?,?,?)", (_now(), kind, text, tags))
        return cur.lastrowid


def _fts_query(q):
    terms = [t.replace('"', "") for t in q.split() if t.replace('"', "")]
    return " ".join('"%s"' % t for t in terms)


def search(query, limit=10):
    query = (query or "").strip()
    with db() as c:
        if not query:
            rows = c.execute("select id, at, kind, text, tags from memories order by id desc limit ?", (limit,)).fetchall()
        elif c.has_fts:
            rows = c.execute("select m.id, m.at, m.kind, m.text, m.tags from memories_fts f join memories m on m.id = f.rowid "
                             "where memories_fts match ? order by rank limit ?", (_fts_query(query), limit)).fetchall()
        else:
            like = "%" + query.replace("%", "") + "%"
            rows = c.execute("select id, at, kind, text, tags from memories where text like ? or tags like ? order by id desc limit ?", (like, like, limit)).fetchall()
        return [dict(r) for r in rows]


def person(name, handle=None, notes=None):
    name = (name or "").strip()
    if not name:
        raise ValueError("a person needs a name")
    with db() as c:
        row = c.execute("select * from people where name = ?", (name,)).fetchone()
        if row:
            c.execute("update people set handle = coalesce(?, handle), notes = coalesce(?, notes), updated = ? where id = ?", (handle, notes, _now(), row["id"]))
            return row["id"]
        return c.execute("insert into people(name, handle, notes, met, updated) values (?,?,?,?,?)", (name, handle, notes, _now(), _now())).lastrowid


def people(limit=50):
    with db() as c:
        return [dict(r) for r in c.execute("select id, name, handle, notes, met, updated from people order by updated desc limit ?", (limit,)).fetchall()]
