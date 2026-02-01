# -*- coding: utf-8 -*-
import sqlite3, sys, os

DB = (len(sys.argv) > 1 and sys.argv[1]) or os.environ.get("RP_DB") or r"C:\RadarPremios\radar_premios.db"

GAME_MAP = {
    "baloto": {
        "res": "baloto_resultados_std",
        "prm": "baloto_premios_std",
        "n5": "baloto_n5sb_std",
    },
    "revancha": {
        "res": "revancha_resultados_std",
        "prm": "revancha_premios_std",
        "n5": "revancha_n5sb_std",
    },
}

def q1(conn, sql, args=()):
    cur = conn.execute(sql, args)
    row = cur.fetchone()
    return row[0] if row else None

def exists(conn, table):
    try:
        conn.execute(f"SELECT 1 FROM {table} LIMIT 1;")
        return True
    except sqlite3.Error:
        return False

def count(conn, table):
    try:
        return q1(conn, f"SELECT COUNT(*) FROM {table};") or 0
    except sqlite3.Error:
        return 0

def main():
    if not os.path.exists(DB):
        print(f"[FATAL] DB no existe: {DB}")
        sys.exit(2)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    overall_bad = False

    print(f"[DB] {DB}")
    for game, cfg in GAME_MAP.items():
        res, prm, n5 = cfg["res"], cfg["prm"], cfg["n5"]
        print("\n" + "="*60)
        print(f"[GAME] {game}")

        for t in [res, prm, n5, "all_n5sb_std"]:
            try:
                ex = exists(conn, t)
                cnt = count(conn, t) if ex else 0
                print(f" - {t:<24} exists={ex} count={cnt}")
            except Exception as e:
                print(f" - {t:<24} error={e}")

        # elegir tabla de features
        feat = n5 if exists(conn, n5) and count(conn, n5) > 0 else "all_n5sb_std"
        print(f" - feature_table elegido: {feat} (count={count(conn, feat)})")

        # unión resultados + premios
        join_rp = 0
        try:
            join_rp = q1(conn, f"""
                SELECT COUNT(*) FROM {res} r
                JOIN {prm} p
                  ON (r.sorteo = p.sorteo) OR (date(r.fecha) = date(p.fecha));
            """) or 0
            print(f" - join res∩prm: {join_rp}")
        except Exception as e:
            print(f" - join res∩prm error: {e}")

        # unión triada resultados + premios + features
        join_rpf = 0
        try:
            join_rpf = q1(conn, f"""
                SELECT COUNT(*) FROM {res} r
                JOIN {prm} p
                  ON (r.sorteo = p.sorteo) OR (date(r.fecha) = date(p.fecha))
                LEFT JOIN {feat} f
                  ON (f.sorteo = r.sorteo) OR (date(f.fecha) = date(r.fecha));
            """) or 0
            print(f" - join res∩prm∩feat: {join_rpf}")
        except Exception as e:
            print(f" - join res∩prm∩feat error: {e}")

        if join_rpf == 0:
            overall_bad = True
            print("   [HINT] El set de entrenamiento queda vacío.")
            print("   [CAUSAS] Llaves desalineadas (sorteo/fecha) o fechas sin normalizar en features.")
            print("   [QUÉ HACER] Crear vista que alinee features por sorteo/fecha o normalizar date().")

    conn.close()
    if overall_bad:
        # código especial para que master.bat pueda reaccionar
        sys.exit(10)
    sys.exit(0)

if __name__ == "__main__":
    main()
