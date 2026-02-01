# std_source.py
# Fuente estándar para juegos de 4 dígitos (y helpers para Baloto N5+SB si se necesita a futuro).
# - Compat con load_draws(..., ascending=True)
# - Prefiere v_matriz_astro_luna_std para astro_luna si existe; si no, usa astro_luna_std (mapeando numero->num).
# - Para "loterias" arma UNION solo de objetos *_std que EXISTEN y tienen columnas (fecha,num|numero).
# - Si existe all_std(fecha,num,game) válido, se usa; si no, se ignora y se construye SQL dinámico.
#
# API usada por score_candidates.py:
#   - connect(db_path) -> sqlite3.Connection
#   - runs_has_column(conn, col) -> bool
#   - load_draws(conn, game=None, ascending=False) -> Iterable[Tuple[str,int]]
#   - sanity_check_source(conn, game=None) -> None (lanza si no hay fuente)

from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional, Tuple


def connect(db_path: str) -> sqlite3.Connection:
    cnx = sqlite3.connect(db_path)
    cnx.row_factory = sqlite3.Row
    return cnx


def runs_has_column(cnx: sqlite3.Connection, col: str) -> bool:
    try:
        rows = cnx.execute("PRAGMA table_info(runs)").fetchall()
        cols = {r["name"] for r in rows}
        return col in cols
    except Exception:
        return False


# ------------------------
# Descubrimiento de fuentes
# ------------------------

def _obj_exists(cnx: sqlite3.Connection, name: str) -> bool:
    q = "SELECT 1 FROM sqlite_master WHERE (type='view' OR type='table') AND name=? LIMIT 1"
    return cnx.execute(q, (name,)).fetchone() is not None


def _has_cols(cnx: sqlite3.Connection, obj: str, want: List[str]) -> bool:
    """Verifica que el objeto (tabla o vista) exponga todas las columnas 'want'."""
    # Estrategia: intentar un SELECT 0 LIMIT 0 y leer cursor.description
    try:
        cur = cnx.execute(f"SELECT * FROM {obj} LIMIT 0")
        got = {d[0] for d in cur.description or []}
        return all(c in got for c in want)
    except Exception:
        return False


def _astro_sql(cnx: sqlite3.Connection) -> Optional[str]:
    # Preferencia 1: v_matriz_astro_luna_std(fecha,num)
    if _obj_exists(cnx, "v_matriz_astro_luna_std") and _has_cols(cnx, "v_matriz_astro_luna_std", ["fecha", "num"]):
        return "SELECT fecha, CAST(num AS INTEGER) AS num FROM v_matriz_astro_luna_std"
    # Preferencia 2: astro_luna_std(fecha,numero)
    if _obj_exists(cnx, "astro_luna_std") and _has_cols(cnx, "astro_luna_std", ["fecha", "numero"]):
        return "SELECT fecha, CAST(numero AS INTEGER) AS num FROM astro_luna_std"
    # Nada.
    return None


def _dynamic_union_sql(cnx: sqlite3.Connection, like_suffix: str = "_std") -> Optional[str]:
    """
    Construye dinámicamente un UNION de todas las vistas/tablas *_std que tengan (fecha, num) o (fecha, numero).
    Devuelve SQL listo para SELECT fecha,num FROM (...).
    Añade columna 'game' si el objeto la tiene; si no, la infiere del prefijo del nombre.
    """
    objs = [r["name"] for r in cnx.execute(
        "SELECT name FROM sqlite_master WHERE (type='view' OR type='table') AND name LIKE ? ORDER BY name",
        (f"%{like_suffix}",)
    )]

    parts: List[str] = []
    for name in objs:
        # ignorar objetos que claramente no son de 4D (p.ej. *_premios_std, *_n5sb_std, etc.)
        low = name.lower()
        if any(tag in low for tag in ("premios", "n5sb", "baloto", "revancha")):
            continue

        if _has_cols(cnx, name, ["fecha", "num"]):
            sel = f"SELECT fecha, CAST(num AS INTEGER) AS num, " \
                  f"(CASE WHEN EXISTS(SELECT 1 FROM pragma_table_info('{name}') WHERE name='game') " \
                  f"THEN game ELSE '{_infer_game_from_name(name)}' END) AS game " \
                  f"FROM {name}"
            parts.append(sel)
        elif _has_cols(cnx, name, ["fecha", "numero"]):
            sel = f"SELECT fecha, CAST(numero AS INTEGER) AS num, " \
                  f"(CASE WHEN EXISTS(SELECT 1 FROM pragma_table_info('{name}') WHERE name='game') " \
                  f"THEN game ELSE '{_infer_game_from_name(name)}' END) AS game " \
                  f"FROM {name}"
            parts.append(sel)

    if not parts:
        return None

    return " UNION ALL ".join(parts)


def _infer_game_from_name(obj_name: str) -> str:
    # ejemplos: "astro_luna_std" -> "astro_luna", "tolima_std" -> "tolima"
    name = obj_name.lower()
    if name.endswith("_std"):
        name = name[:-4]
    return name


def _valid_all_std(cnx: sqlite3.Connection) -> bool:
    return _obj_exists(cnx, "all_std") and _has_cols(cnx, "all_std", ["fecha", "num"]) and (
        _has_cols(cnx, "all_std", ["game"]) or True  # si no trae 'game' igualmente puede servir si pasamos un único juego
    )


def _source_sql_for_game(cnx: sqlite3.Connection, game: Optional[str]) -> Tuple[str, Optional[Tuple]]:
    """
    Devuelve: (sql, params) donde sql selecciona al menos columnas (fecha,num)
    Si 'game' es:
      - 'astro_luna' -> usa fuente Astro (preferencias)
      - 'loterias'   -> UNION dinámico de *_std (excluye premios/N5SB)
      - None/'any'   -> intenta 'all_std'; si inválida, usa UNION dinámico incluyendo astro si existe
    """
    g = (game or "").strip().lower() or "any"

    # 1) Si piden explícitamente astro_luna
    if g in ("astro", "astro_luna", "astroluna"):
        sql = _astro_sql(cnx)
        if sql:
            return sql, None
        # fallback: dynamic union y filtrar por game si existe
        union_sql = _dynamic_union_sql(cnx)
        if union_sql:
            return f"SELECT fecha, num FROM ({union_sql}) WHERE game IN ('astro','astro_luna','astroluna')", None
        raise RuntimeError("No se encontró una fuente válida para astro_luna (ni v_matriz_astro_luna_std ni astro_luna_std).")

    # 2) Loterías (regionales de 4D)
    if g in ("loterias", "lotería", "loteria"):
        union_sql = _dynamic_union_sql(cnx)
        if union_sql:
            return f"SELECT fecha, num FROM ({union_sql})", None
        # fallback: si all_std es válida y trae 4D, úsala
        if _valid_all_std(cnx):
            # si all_std tiene 'game' podemos filtrar a lo que no sea baloto/revancha
            # pero como ya filtramos N5SB/premios en union, aquí devolvemos tal cual
            return "SELECT fecha, CAST(num AS INTEGER) AS num FROM all_std", None
        raise RuntimeError("No hay vistas *_std 4D disponibles para loterías y 'all_std' no es utilizable.")

    # 3) Any / genérico
    if _valid_all_std(cnx):
        # Si all_std tiene 'game', permitimos filtrar por uno en específico si llega distinto de 'any'
        if game and game.lower() not in ("any", "") and _has_cols(cnx, "all_std", ["game"]):
            return "SELECT fecha, CAST(num AS INTEGER) AS num FROM all_std WHERE lower(game)=lower(?)", (game,)
        return "SELECT fecha, CAST(num AS INTEGER) AS num FROM all_std", None

    # Fallback general: union dinámico (incluye astro si existe) 
    union_sql = _dynamic_union_sql(cnx)
    astro = _astro_sql(cnx)
    parts: List[str] = []
    if union_sql:
        parts.append(union_sql)  # ya proyecta fecha,num,game
    if astro:
        parts.append(f"SELECT fecha, num, 'astro_luna' AS game FROM ({astro})")
    if not parts:
        raise RuntimeError("No se encontraron fuentes *_std (4 dígitos) utilizable(s).")

    any_sql = " UNION ALL ".join(parts)
    if game and game.lower() not in ("any", ""):
        return f"SELECT fecha, num FROM ({any_sql}) WHERE lower(game)=lower(?)", (game,)
    return f"SELECT fecha, num FROM ({any_sql})", None


# ------------------------
# API pública usada por scoring
# ------------------------

def load_draws(
    cnx: sqlite3.Connection,
    game: Optional[str] = None,
    ascending: bool = False  # compat con llamadas existentes
) -> Iterable[Tuple[str, int]]:
    """
    Devuelve iterador de (fecha:str, num:int) ordenado por fecha.
    """
    sql, params = _source_sql_for_game(cnx, game)
    order = "ASC" if ascending else "DESC"
    q = f"SELECT fecha, CAST(num AS INTEGER) AS num FROM ({sql}) ORDER BY fecha {order}"
    cur = cnx.execute(q, params or ())
    for r in cur:
        yield (r["fecha"], int(r["num"]))


def sanity_check_source(cnx: sqlite3.Connection, game: Optional[str] = None) -> None:
    sql, params = _source_sql_for_game(cnx, game)
    cnx.execute(f"SELECT fecha, num FROM ({sql}) LIMIT 1", params or ())
