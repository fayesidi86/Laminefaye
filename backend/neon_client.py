"""
neon_client.py - Drop-in replacement for the Supabase Python client.
Provides the same .table().select().eq().execute() chainable interface
using psycopg2 to connect directly to Neon PostgreSQL.
"""
import psycopg2
import psycopg2.extras
import json
import os
import logging

logger = logging.getLogger("neon-client")

# Primary keys per table (for upsert conflict resolution)
_TABLE_PKS = {
    "categories": "id",
    "products": "id",
    "settings": "key",
}


class NeonResult:
    """Mimics Supabase's execute() result with a .data attribute."""
    def __init__(self, data=None):
        self.data = data if data is not None else []


class NeonQueryBuilder:
    """Chainable query builder that mimics Supabase's PostgREST interface."""

    def __init__(self, conn_func, table, operation, columns=None, values=None):
        self._conn_func = conn_func
        self._table = table
        self._op = operation
        self._columns = columns
        self._values = values
        self._wheres = []
        self._or_filter = None
        self._order_col = None
        self._order_desc = False

    def eq(self, column, value):
        self._wheres.append((column, "=", value))
        return self

    def order(self, column, desc=False):
        self._order_col = column
        self._order_desc = desc
        return self

    def or_(self, filter_str):
        self._or_filter = filter_str
        return self

    def execute(self):
        conn = self._conn_func()
        try:
            if self._op == "select":
                return self._do_select(conn)
            elif self._op == "insert":
                return self._do_insert(conn)
            elif self._op == "update":
                return self._do_update(conn)
            elif self._op == "delete":
                return self._do_delete(conn)
            elif self._op == "upsert":
                return self._do_upsert(conn)
        except psycopg2.Error as e:
            logger.error(f"Database error ({self._op} on {self._table}): {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            raise

    # ------------------------------------------------------------------ WHERE
    def _build_where(self):
        clauses, params = [], []
        for col, op, val in self._wheres:
            clauses.append(f'"{col}" {op} %s')
            params.append(val)
        if self._or_filter:
            or_parts = []
            for part in self._or_filter.split(","):
                segs = part.strip().split(".", 2)
                if len(segs) == 3:
                    col, op, val = segs
                    if op == "ilike":
                        or_parts.append(f'"{col}" ILIKE %s')
                        params.append(val)
            if or_parts:
                clauses.append(f"({' OR '.join(or_parts)})")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        return where, params

    # ----------------------------------------------------------------- SELECT
    def _do_select(self, conn):
        cols = self._columns or "*"
        where, params = self._build_where()
        order = ""
        if self._order_col:
            d = "DESC" if self._order_desc else "ASC"
            order = f' ORDER BY "{self._order_col}" {d}'
        sql = f'SELECT {cols} FROM "{self._table}"{where}{order}'
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(sql, params or None)
            return NeonResult([dict(r) for r in cur.fetchall()])
        finally:
            cur.close()

    # ----------------------------------------------------------------- INSERT
    def _do_insert(self, conn):
        rows = self._values if isinstance(self._values, list) else [self._values]
        if not rows:
            return NeonResult([])
        columns = list(rows[0].keys())
        col_str = ", ".join(f'"{c}"' for c in columns)
        ph = ", ".join(["%s"] * len(columns))
        sql = f'INSERT INTO "{self._table}" ({col_str}) VALUES ({ph}) RETURNING *'
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        results = []
        try:
            for row in rows:
                vals = [_adapt(row.get(c)) for c in columns]
                cur.execute(sql, vals)
                r = cur.fetchone()
                if r:
                    results.append(dict(r))
            conn.commit()
            return NeonResult(results)
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    # ----------------------------------------------------------------- UPDATE
    def _do_update(self, conn):
        if not self._values:
            return NeonResult([])
        set_parts, params = [], []
        for col, val in self._values.items():
            set_parts.append(f'"{col}" = %s')
            params.append(_adapt(val))
        where, wp = self._build_where()
        params.extend(wp)
        sql = f'UPDATE "{self._table}" SET {", ".join(set_parts)}{where} RETURNING *'
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            conn.commit()
            return NeonResult(rows)
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    # ----------------------------------------------------------------- DELETE
    def _do_delete(self, conn):
        where, params = self._build_where()
        sql = f'DELETE FROM "{self._table}"{where}'
        cur = conn.cursor()
        try:
            cur.execute(sql, params or None)
            conn.commit()
            return NeonResult([])
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    # ----------------------------------------------------------------- UPSERT
    def _do_upsert(self, conn):
        if not self._values:
            return NeonResult([])
        pk = _TABLE_PKS.get(self._table, "id")
        columns = list(self._values.keys())
        col_str = ", ".join(f'"{c}"' for c in columns)
        ph = ", ".join(["%s"] * len(columns))
        non_pk = [c for c in columns if c != pk]
        update_str = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in non_pk)
        sql = f'INSERT INTO "{self._table}" ({col_str}) VALUES ({ph})'
        if update_str:
            sql += f' ON CONFLICT ("{pk}") DO UPDATE SET {update_str}'
        else:
            sql += f' ON CONFLICT ("{pk}") DO NOTHING'
        sql += " RETURNING *"
        vals = [_adapt(self._values.get(c)) for c in columns]
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(sql, vals)
            row = cur.fetchone()
            conn.commit()
            return NeonResult([dict(row)] if row else [])
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def _adapt(value):
    """Convert Python lists/dicts to JSON strings for JSONB columns."""
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return value


class NeonTableRef:
    """Represents a table with chainable select/insert/update/delete/upsert."""

    def __init__(self, conn_func, table_name):
        self._conn_func = conn_func
        self._table = table_name

    def select(self, columns="*"):
        return NeonQueryBuilder(self._conn_func, self._table, "select", columns=columns)

    def insert(self, values):
        return NeonQueryBuilder(self._conn_func, self._table, "insert", values=values)

    def update(self, values):
        return NeonQueryBuilder(self._conn_func, self._table, "update", values=values)

    def delete(self):
        return NeonQueryBuilder(self._conn_func, self._table, "delete")

    def upsert(self, values):
        return NeonQueryBuilder(self._conn_func, self._table, "upsert", values=values)


class NeonClient:
    """Drop-in replacement for supabase.create_client().

    Usage::

        client = NeonClient(database_url)
        result = client.table("products").select("*").eq("id", "123").execute()
        print(result.data)  # [{"id": "123", "title": "...", ...}]
    """

    def __init__(self, database_url=None):
        self._url = database_url or os.getenv("DATABASE_URL", "")
        if not self._url:
            raise RuntimeError("DATABASE_URL not set")
        self._conn = None

    def _get_conn(self):
        """Return a live connection, reconnecting if needed."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self._url)
        return self._conn

    def table(self, name):
        return NeonTableRef(self._get_conn, name)

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
