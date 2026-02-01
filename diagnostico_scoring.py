# -*- coding: utf-8 -*-
import argparse, sqlite3, sys

OK="OK"; WARN="WARN"; ERR="ERR"

def exists(conn, name):
    cur=conn.execute("select 1 from sqlite_master where type in ('table','view') and name=?;", (name,))
    return cur.fetchone() is not None

def count(conn, name):
    try:
        return conn.execute(f"select count(*) from {name};").fetchone()[0]
    except Exception:
        return None

def has_cols(conn, name, cols):
    try:
        got = {r[1] for r in conn.execute(f"PRAGMA table_info({name});")}
        miss=[c for c in cols if c not in got]
        return miss
    except Exception:
        return cols

def line(state,msg):
    tag={"OK":"[OK ]","WARN":"[WARN]","ERR":"[ERR]"}[state]
    print(f"{tag} {msg}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--game", choices=["baloto","revancha"], required=True)
    ap.add_argument("--min", type=int, default=60)
    args=ap.parse_args()

    conn=sqlite3.connect(args.db)
    problems=0

    # Conjuntos esperados
    game=args.game
    resultados=f"{game}_resultados"
    resultados_std=f"{game}_resultados_std"
    premios=f"{game}_premios"
    premios_std=f"{game}_premios_std"
    n5sb_std=f"{game}_n5sb_std"

    required_tables=[resultados, resultados_std, premios, premios_std]
    optional_tables=[n5sb_std]

    print("=== DIAGNÓSTICO SCORING ===")
    for t in required_tables:
        if not exists(conn,t):
            line(ERR,f"No existe tabla requerida: {t}")
            problems+=1
        else:
            c=count(conn,t)
            if c is None:
                line(ERR,f"Error contando filas en: {t}")
                problems+=1
            else:
                state = OK if c>=args.min else ERR
                if state==ERR: problems+=1
                line(state,f"{t}: filas={c} (min={args.min})")

    for t in optional_tables:
        if exists(conn,t):
            line(OK,f"{t}: existe (opcional)")
        else:
            line(WARN,f"{t}: no existe (opcional)")

    # Columnas clave
    cols_res_min=["sorteo","fecha"]
    cols_prem_min=["sorteo","fecha","modo","aciertos","ganadores","premio_total"]
    for t, cols in [(resultados_std, cols_res_min),
                    (premios_std, cols_prem_min)]:
        if exists(conn,t):
            miss=has_cols(conn,t,cols)
            if miss:
                line(ERR,f"{t}: faltan columnas {miss}")
                problems+=1
            else:
                line(OK,f"{t}: columnas clave presentes")

    # Fechas y sorteos cruzables
    try:
        cur=conn.execute(f"""
            select count(*) 
            from {resultados_std} r 
            join {premios_std} p 
              on p.sorteo=r.sorteo
            where r.fecha is not null and p.fecha is not null
        """)
        cross=cur.fetchone()[0]
        line(OK if cross>=args.min else WARN,
             f"Cruces resultados↔premios por sorteo: {cross} (min sugerido {args.min})")
        if cross<args.min: problems+=1
    except Exception as e:
        line(ERR,f"Error verificando cruces resultados↔premios: {e}")
        problems+=1

    # Nulos críticos
    try:
        null_res=conn.execute(f"select count(*) from {resultados_std} where fecha is null or sorteo is null;").fetchone()[0]
        null_pre=conn.execute(f"select count(*) from {premios_std} where fecha is null or sorteo is null;").fetchone()[0]
        line(OK if null_res==0 else WARN, f"{resultados_std}: registros con sorteo/fecha nulos = {null_res}")
        line(OK if null_pre==0 else WARN, f"{premios_std}: registros con sorteo/fecha nulos = {null_pre}")
        if null_res>0 or null_pre>0: problems+=1
    except Exception as e:
        line(ERR,f"Error revisando nulos: {e}")
        problems+=1

    # Último sorteo disponible (sanity)
    try:
        last_res=conn.execute(f"select max(sorteo) from {resultados_std};").fetchone()[0]
        last_pre=conn.execute(f"select max(sorteo) from {premios_std};").fetchone()[0]
        line(OK, f"Último sorteo resultados={last_res} | premios={last_pre}")
    except Exception:
        pass

    # Salida
    if problems:
        print(f"[EXIT] Problemas detectados={problems} -> RC=3")
        sys.exit(3)
    print("[EXIT] Diagnóstico OK -> RC=0")
    sys.exit(0)

if __name__=="__main__":
    main()
