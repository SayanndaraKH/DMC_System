"""
Migrate the DMS database from one Neon project/region to another.

Purpose: the current Neon project lives in us-east-1, which costs ~263ms round-trip
from Cambodia. Every query pays that. Moving to ap-southeast-1 (Singapore) brings it
to roughly 30ms. Neon cannot move an existing project between regions, so this copies
the data into a brand new project.

No pg_dump / psql required - this streams table data over COPY using psycopg2.

Usage:
    # 1. See what would be copied and how big it is (touches nothing)
    python migrate_neon_region.py --plan

    # 2. Create the schema on the new database (runs Django migrate against it)
    python migrate_neon_region.py --target "<new-neon-url>" --create-schema

    # 3. Copy the data
    python migrate_neon_region.py --target "<new-neon-url>" --copy

    # 4. Confirm source and target match, and compare latency
    python migrate_neon_region.py --target "<new-neon-url>" --verify

Afterwards, point DATABASE_URL in .env at the new URL. run.py now loads .env before
applying its hardcoded fallback, so that single edit is enough.
"""

import os
import io
import re
import sys
import time
import argparse
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

# Load .env the same way run.py/settings.py do, so --plan uses the live source DB.
ENV_FILE = BASE_DIR / '.env'
if ENV_FILE.exists():
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dms_project.settings')

import psycopg2  # noqa: E402


def log(msg):
    print(msg, flush=True)


def region_of(url):
    m = re.search(r'\.([a-z]+-[a-z]+-\d)\.aws', url or '')
    return m.group(1) if m else 'unknown'


def source_url():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        sys.exit("DATABASE_URL is not set - cannot determine the source database.")
    return url


def ordered_tables():
    """
    Returns table names ordered so that a table is always copied after the tables
    it points at, which keeps foreign keys valid without disabling constraints
    (Neon does not grant the superuser rights needed for session_replication_role).
    """
    import django
    django.setup()
    from django.apps import apps

    # include_auto_created picks up the many-to-many through tables (auth_user_groups,
    # dms_leadershipannotation_target_departments, ...). They are empty today but
    # skipping them would silently drop data once they are used.
    models = [m for m in apps.get_models(include_auto_created=True) if m._meta.managed]
    table_of = {m: m._meta.db_table for m in models}

    # Only forward FK/O2O columns count as dependencies. get_fields() would also
    # return reverse relations, which makes every parent look like it depends on
    # its children and produces a false cycle (auth_user <-> dms_userprofile).
    deps = {m: set() for m in models}
    for m in models:
        for f in m._meta.concrete_fields:
            if f.remote_field is not None and (f.many_to_one or f.one_to_one):
                rel = f.remote_field.model
                if rel in deps and rel is not m:
                    deps[m].add(rel)

    ordered, seen = [], set()

    def visit(m, stack):
        if m in seen:
            return
        if m in stack:          # circular FK - caller handles with a second pass
            return
        stack.add(m)
        for d in deps[m]:
            visit(d, stack)
        stack.discard(m)
        seen.add(m)
        ordered.append(m)

    for m in models:
        visit(m, set())

    # Django's own bookkeeping tables are not in apps.get_models() for content types
    # order purposes, but they are real models, so this list already covers them.
    return [table_of[m] for m in ordered]


def live_counts(conn, tables):
    counts = {}
    with conn.cursor() as c:
        for t in tables:
            try:
                c.execute(f'SELECT count(*) FROM "{t}"')
                counts[t] = c.fetchone()[0]
            except Exception:
                conn.rollback()
                counts[t] = None
    return counts


def cmd_plan():
    src = source_url()
    log(f"Source region : {region_of(src)}")
    tables = ordered_tables()
    conn = psycopg2.connect(src)
    counts = live_counts(conn, tables)
    with conn.cursor() as c:
        c.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        size = c.fetchone()[0]
    log(f"Database size : {size}")
    log(f"Tables        : {len(tables)}")
    log("")
    log(f"{'#':>3}  {'table':<42}{'rows':>9}")
    total = 0
    for i, t in enumerate(tables, 1):
        n = counts.get(t)
        if n:
            total += n
        log(f"{i:>3}  {t:<42}{'-' if n is None else n:>9}")
    log("")
    log(f"TOTAL ROWS TO COPY: {total}")
    log("Copy order above is FK-safe (parents before children).")
    conn.close()


def cmd_create_schema(target):
    log(f"Target region : {region_of(target)}")
    log("Running Django migrate against the target database...")
    env = dict(os.environ)
    env['DATABASE_URL'] = target
    env['USE_LOCAL_SQLITE'] = 'False'
    r = subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'],
                       env=env, cwd=str(BASE_DIR))
    if r.returncode != 0:
        sys.exit("migrate failed on the target database - schema not created.")
    log("Schema created on target.")


def cmd_copy(target, text_format=False):
    src = source_url()
    if region_of(src) == region_of(target) and src == target:
        sys.exit("Source and target are the same database - refusing to copy.")

    log(f"Copying {region_of(src)} -> {region_of(target)}")
    tables = ordered_tables()

    # Keepalives stop Neon/NAT from silently dropping a long bulk transfer.
    ka = dict(keepalives=1, keepalives_idle=30, keepalives_interval=10,
              keepalives_count=5, connect_timeout=30)
    s_conn = psycopg2.connect(src, **ka)
    t_conn = psycopg2.connect(target, **ka)

    def major(conn):
        with conn.cursor() as c:
            c.execute("SHOW server_version")
            return int(c.fetchone()[0].split('.')[0])

    s_major, t_major = major(s_conn), major(t_conn)
    log(f"Postgres: source {s_major}, target {t_major}")
    if s_major != t_major and not text_format:
        sys.exit(
            f"Source is Postgres {s_major} but target is {t_major}. The BINARY copy "
            f"format is not portable across major versions. Either create the target "
            f"project with Postgres {s_major}, or re-run with --text-format."
        )

    # The version probes above opened a transaction on each connection; close them
    # so the copy below starts clean (psycopg2 defaults to autocommit=False).
    s_conn.rollback()
    t_conn.rollback()

    counts = live_counts(s_conn, tables)
    nonempty = [t for t in tables if counts.get(t)]

    # Primary key column per table, used for chunking and resuming.
    from django.apps import apps
    pk_of = {}
    for mdl in apps.get_models(include_auto_created=True):
        if mdl._meta.managed:
            pk_of[mdl._meta.db_table] = mdl._meta.pk.column

    def target_state(table):
        """(row count, max pk) currently on the target."""
        cnt, mx = 0, None
        with t_conn.cursor() as tc:
            tc.execute(f'SELECT count(*) FROM "{table}"')
            cnt = tc.fetchone()[0]
            pk = pk_of.get(table)
            if pk and cnt:
                try:
                    tc.execute(f'SELECT max("{pk}") FROM "{table}"')
                    mx = tc.fetchone()[0]
                except Exception:
                    t_conn.rollback()
        t_conn.commit()
        return cnt, mx

    # BINARY is faster but its wire format is tied to the Postgres major version,
    # so it is only safe when source and target majors match. TEXT is portable.
    fmt = 'TEXT' if text_format else 'BINARY'
    grand_total = 0
    t_start = time.time()

    for i, t in enumerate(nonempty, 1):
        n = counts[t]
        tcount, tmax = target_state(t)

        if tcount == n:
            log(f"  [{i:>3}/{len(nonempty)}] {t:<40}{n:>8} rows  already complete, skipped")
            grand_total += n
            continue

        pk = pk_of.get(t)
        resume_from = tmax if (pk and tcount and isinstance(tmax, int)) else None
        if resume_from is None and tcount:
            with t_conn.cursor() as tc:
                tc.execute(f'DELETE FROM "{t}"')
            t_conn.commit()
            tcount = 0

        # Large tables are copied in chunks so memory stays bounded, progress is
        # visible, and an interrupted run resumes instead of restarting. Buffering
        # one 353MB table over a 250ms link is what stalled the first attempt.
        use_chunks = bool(pk) and n > 200
        if not use_chunks:
            buf = io.BytesIO()
            with s_conn.cursor() as sc:
                sc.copy_expert(f'COPY "{t}" TO STDOUT WITH (FORMAT {fmt})', buf)
            buf.seek(0)
            with t_conn.cursor() as tc:
                try:
                    tc.copy_expert(f'COPY "{t}" FROM STDIN WITH (FORMAT {fmt})', buf)
                except Exception as e:
                    t_conn.rollback()
                    sys.exit(f"Copy failed on {t}: {e}")
            t_conn.commit()
            grand_total += n
            log(f"  [{i:>3}/{len(nonempty)}] {t:<40}{n:>8} rows  ({buf.tell()/1048576:.1f} MB)")
            continue

        # Target roughly 4MB per COPY so one batch never becomes a huge,
        # stall-prone transfer. Derived from the table's average row size.
        try:
            with s_conn.cursor() as sc:
                sc.execute(f"SELECT pg_total_relation_size('\"{t}\"')")
                avg_row = max(1, sc.fetchone()[0] // max(n, 1))
            s_conn.rollback()
        except Exception:
            s_conn.rollback()
            avg_row = 1024
        batch = max(1, min(2000, (4 * 1024 * 1024) // avg_row))
        done, last, mb = tcount, resume_from, 0.0
        tt0 = time.time()
        if done:
            log(f"  [{i:>3}/{len(nonempty)}] {t:<40}{n:>8} rows  resuming from {done}")

        def reconnect_source():
            """Neon drops long-running COPY connections; rebuild and carry on."""
            nonlocal s_conn
            try:
                s_conn.close()
            except Exception:
                pass
            s_conn = psycopg2.connect(src, **ka)

        # Batch size adapts: this table holds rows up to 23MB, so a fixed 20-row
        # batch becomes a ~100MB single COPY that stalls and drops the connection.
        # On failure we halve the batch (down to one row) instead of giving up.
        fails = 0
        while done < n:
            where = f'WHERE "{pk}" > {last}' if last is not None else ''

            # Find this batch's id range using ONLY the pk column. Deriving it from
            # SELECT * would make Postgres re-read every blob just to compute a max.
            try:
                with s_conn.cursor() as sc:
                    sc.execute(f'SELECT max(q."{pk}") FROM (SELECT "{pk}" FROM "{t}" '
                               f'{where} ORDER BY "{pk}" LIMIT {batch}) q')
                    batch_max = sc.fetchone()[0]
                s_conn.rollback()
            except Exception as e:
                log(f"      source lost while planning batch ({e}); reconnecting...")
                reconnect_source()
                continue

            if batch_max is None:
                break

            rng = (f'WHERE "{pk}" > {last} AND "{pk}" <= {batch_max}' if last is not None
                   else f'WHERE "{pk}" <= {batch_max}')
            sel = f'SELECT * FROM "{t}" {rng} ORDER BY "{pk}"'

            try:
                buf = io.BytesIO()
                with s_conn.cursor() as sc:
                    sc.copy_expert(f'COPY ({sel}) TO STDOUT WITH (FORMAT {fmt})', buf)
                s_conn.rollback()
            except Exception as e:
                fails += 1
                reconnect_source()
                if batch > 1:
                    batch = max(1, batch // 4)
                    log(f"      batch too large ({e}); retrying with batch={batch}")
                    continue
                if fails > 12:
                    sys.exit(f"Giving up on {t} after {done} rows. Re-run --copy to resume.")
                log(f"      read failed at batch=1 (fail {fails}/12): {e}; retrying")
                time.sleep(3)
                continue

            if buf.tell() == 0:
                last = batch_max
                continue

            buf.seek(0)
            try:
                with t_conn.cursor() as tc:
                    tc.copy_expert(f'COPY "{t}" FROM STDIN WITH (FORMAT {fmt})', buf)
                t_conn.commit()
            except Exception as e:
                # Neon also drops the TARGET side mid-COPY. The failed batch is rolled
                # back server-side, so reconnect, re-read where the target really is,
                # and retry from there with a smaller batch.
                fails += 1
                try:
                    t_conn.rollback()
                except Exception:
                    pass
                if fails > 12:
                    sys.exit(f"Copy failed on {t} after {done} rows: {e}. Re-run --copy to resume.")
                log(f"      target write failed (fail {fails}/12): {e}; reconnecting target...")
                time.sleep(3)
                try:
                    t_conn.close()
                except Exception:
                    pass
                try:
                    t_conn = psycopg2.connect(target, **ka)
                    done, last = target_state(t)
                except Exception as e2:
                    log(f"      target reconnect failed: {e2}")
                    t_conn = psycopg2.connect(target, **ka)
                    done, last = target_state(t)
                batch = max(1, batch // 2)
                continue

            mb += buf.tell() / 1048576
            done, _ = target_state(t)
            last = batch_max
            fails = 0
            rate = mb / max(time.time() - tt0, 0.1)
            log(f"      {t:<30}{done:>7}/{n}  {done*100//n:>3}%  {mb:7.1f} MB  "
                f"{rate:5.2f} MB/s  batch={batch}")

        done, _ = target_state(t)

        grand_total += done
        log(f"  [{i:>3}/{len(nonempty)}] {t:<40}{done:>8} rows  DONE ({mb:.1f} MB)")

    log(f"\nCopied {grand_total} rows in {time.time()-t_start:.0f}s")

    # Sequences must be advanced past the copied ids or the next insert collides.
    log("Resetting sequences on target...")
    with t_conn.cursor() as tc:
        tc.execute("""
            SELECT 'SELECT setval(' || quote_literal(quote_ident(ns.nspname)||'.'||quote_ident(s.relname))
                   || ', COALESCE((SELECT MAX(' || quote_ident(a.attname) || ') FROM '
                   || quote_ident(ns.nspname)||'.'||quote_ident(t.relname) || '), 1), true);'
            FROM pg_class s
            JOIN pg_depend d ON d.objid = s.oid AND d.classid='pg_class'::regclass AND d.refclassid='pg_class'::regclass
            JOIN pg_class t ON t.oid = d.refobjid
            JOIN pg_namespace ns ON ns.oid = s.relnamespace
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
            WHERE s.relkind='S'
        """)
        stmts = [r[0] for r in tc.fetchall()]
        for st in stmts:
            tc.execute(st)
    t_conn.commit()
    log(f"Reset {len(stmts)} sequences.")

    s_conn.close()
    t_conn.close()
    log("\nCopy complete. Run --verify next.")


def cmd_verify(target):
    src = source_url()
    tables = ordered_tables()
    s_conn = psycopg2.connect(src)
    t_conn = psycopg2.connect(target)

    sc = live_counts(s_conn, tables)
    tc = live_counts(t_conn, tables)

    mismatches = []
    for t in tables:
        if (sc.get(t) or 0) != (tc.get(t) or 0):
            mismatches.append((t, sc.get(t), tc.get(t)))

    log(f"{'table':<42}{'source':>9}{'target':>9}")
    for t in tables:
        if sc.get(t) or tc.get(t):
            flag = '' if (sc.get(t) or 0) == (tc.get(t) or 0) else '   <-- MISMATCH'
            log(f"{t:<42}{sc.get(t) or 0:>9}{tc.get(t) or 0:>9}{flag}")

    log("")
    if mismatches:
        log(f"FAILED: {len(mismatches)} table(s) differ. Do not switch DATABASE_URL yet.")
    else:
        log("OK: every table matches.")

    # Latency comparison - the whole point of the move.
    def rtt(conn):
        best = 1e9
        with conn.cursor() as c:
            for _ in range(5):
                t0 = time.time()
                c.execute("SELECT 1")
                c.fetchone()
                best = min(best, (time.time() - t0) * 1000)
        return best

    log("")
    log(f"Round-trip {region_of(src):<16}: {rtt(s_conn):7.0f} ms")
    log(f"Round-trip {region_of(target):<16}: {rtt(t_conn):7.0f} ms")

    s_conn.close()
    t_conn.close()
    if mismatches:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="Migrate the DMS database to a new Neon region.")
    ap.add_argument('--target', help='Connection URL of the new Neon database')
    ap.add_argument('--plan', action='store_true', help='Show what would be copied')
    ap.add_argument('--create-schema', action='store_true', help='Run Django migrate on target')
    ap.add_argument('--copy', action='store_true', help='Copy all data to target')
    ap.add_argument('--verify', action='store_true', help='Compare row counts and latency')
    ap.add_argument('--text-format', action='store_true',
                    help='Copy using TEXT instead of BINARY (needed if Postgres majors differ)')
    a = ap.parse_args()

    if a.plan:
        return cmd_plan()
    if not a.target:
        ap.error("--target is required for --create-schema / --copy / --verify")
    if a.create_schema:
        return cmd_create_schema(a.target)
    if a.copy:
        return cmd_copy(a.target, text_format=a.text_format)
    if a.verify:
        return cmd_verify(a.target)
    ap.print_help()


if __name__ == '__main__':
    main()
