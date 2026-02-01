# -*- coding: utf-8 -*-
import sqlite3, sys, os

DB = (len(sys.argv) > 1 and sys.argv[1]) or os.environ.get("RP_DB") or r"C:\RadarPremios\radar_premios.db"

def recent(conn, res, prm, feat, limit=100):
    sql = f"""
    WITH r AS (
      SELECT sorteo, date(fecha) AS fecha
      FROM {res}
      WHERE fecha IS NOT NULL OR sorteo IS NOT NULL
      ORDER BY fecha DESC, sorteo DESC
      LIMIT {limit}
    )
    SELECT
      (SELECT COUNT(*) FROM r) AS r_cnt,
      (SELECT COUNT(*) FROM r JOIN {prm} p ON (r.sorteo=p.sorteo OR r.fecha=date(p.fecha))) AS rp_cnt,
      (SELECT COUNT(*) FROM r
         JOIN {prm} p ON (r.sorteo=p.sorteo OR r.fecha=date(p.fecha))
         LEFT JOIN {feat} f ON (r.sorteo=f.sorteo OR r.fecha=date(f.fecha))
      ) AS rpf_cnt;
    """
    return conn.execute(sql).fetchone()

def main():
    if not os.path.exists(DB):
        print(f"[FATAL] DB no existe: {DB}"); sys.exit(2)
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row

    cases = [
        ("baloto","baloto_resultados_std","baloto_premios_std","baloto_n5sb_std"),
        ("revancha","revancha_resultados_std","revancha_premios_std","revancha_n5sb_std"),
    ]

    bad = False
    for game, res, prm, feat in cases:
        # fallback a all_n5sb_std si no hay features del juego
        try:
            conn.execute(f"SELECT 1 FROM {feat} LIMIT 1;")
        except:
            feat = "all_n5sb_std"

        print("\n" + "="*60)
        print(f"[GAME] {game} (feat={feat})")
        try:
            r_cnt, rp_cnt, rpf_cnt = recent(conn, res, prm, feat, limit=100)
            print(f" - recientes resultados: {r_cnt}")
            print(f" - con premios:          {rp_cnt}")
            print(f" - con premios+features: {rpf_cnt}")
            if rpf_cnt == 0:
                bad = True
                print("   [HINT] Features no alinean con recientes; normaliza date() o mapea sorteo.")
        except Exception as e:
            bad = True
            print(f"   [ERR] diag recientes: {e}")

    conn.close()
    sys.exit(11 if bad else 0)

if __name__ == "__main__":
    main()
