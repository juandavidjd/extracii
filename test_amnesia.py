#!/usr/bin/env python3
"""
ODI — Test de Amnesia (PR-V2.0)
===============================
Valida que la memoria persiste después de reinicio.

USO:
    1. Ejecutar ANTES del reinicio:
       python test_amnesia.py --setup
    
    2. Reiniciar contenedor:
       docker compose restart odi-voice
    
    3. Ejecutar DESPUÉS del reinicio:
       python test_amnesia.py --verify
    
CRITERIO DE ÉXITO:
    Si --verify muestra los datos de --setup → APROBADO
"""

import sys
import os

# Ajustar path para importar desde el mismo directorio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from persistent_memory import PersistentMemoryL1, get_memory

TEST_USER = "test_amnesia_user"
TEST_FACT_KEY = "amnesia_test_value"
TEST_FACT_VALUE = "ODI_SOBREVIVE_REINICIO_2026"
TEST_EVENT_INTENT = "AMNESIA_TEST"
TEST_EVENT_OUTCOME = "SUCCESS"


def setup_test():
    """Fase 1: Escribir datos de prueba."""
    print("=" * 60)
    print("ODI TEST DE AMNESIA — FASE 1: SETUP")
    print("=" * 60)
    
    mem = get_memory()
    
    # Escribir hecho
    mem.set_fact(TEST_USER, TEST_FACT_KEY, TEST_FACT_VALUE)
    print(f"✓ Hecho escrito: {TEST_FACT_KEY} = {TEST_FACT_VALUE}")
    
    # Escribir flag
    mem.set_flag(TEST_USER, "amnesia_tested", True)
    print(f"✓ Flag escrito: amnesia_tested = True")
    
    # Escribir evento
    mem.add_event(TEST_USER, TEST_EVENT_INTENT, TEST_EVENT_OUTCOME)
    print(f"✓ Evento registrado: {TEST_EVENT_INTENT} → {TEST_EVENT_OUTCOME}")
    
    # Mostrar snapshot
    snapshot = mem.snapshot(TEST_USER)
    print("\n📋 Snapshot guardado:")
    print(f"   Facts: {snapshot['user']['facts']}")
    print(f"   Flags: {snapshot['user']['flags']}")
    print(f"   Events: {len(snapshot['user']['events'])} registrados")
    
    print("\n" + "=" * 60)
    print("AHORA EJECUTA:")
    print("   docker compose restart odi-voice")
    print("LUEGO EJECUTA:")
    print("   python test_amnesia.py --verify")
    print("=" * 60)


def verify_test():
    """Fase 2: Verificar que los datos persisten."""
    print("=" * 60)
    print("ODI TEST DE AMNESIA — FASE 2: VERIFY")
    print("=" * 60)
    
    mem = get_memory()
    
    # Verificar usuario existe
    if not mem.user_exists(TEST_USER):
        print("❌ FALLO: Usuario no existe después del reinicio")
        return False
    
    print(f"✓ Usuario {TEST_USER} existe")
    
    # Verificar hecho
    fact_value = mem.get_fact(TEST_USER, TEST_FACT_KEY)
    if fact_value == TEST_FACT_VALUE:
        print(f"✓ Hecho persistido: {TEST_FACT_KEY} = {fact_value}")
    else:
        print(f"❌ FALLO: Hecho perdido o corrupto")
        print(f"   Esperado: {TEST_FACT_VALUE}")
        print(f"   Obtenido: {fact_value}")
        return False
    
    # Verificar flag
    flag_value = mem.get_flag(TEST_USER, "amnesia_tested")
    if flag_value:
        print(f"✓ Flag persistido: amnesia_tested = {flag_value}")
    else:
        print(f"❌ FALLO: Flag perdido")
        return False
    
    # Verificar evento
    last_event = mem.get_last_event(TEST_USER)
    if last_event and last_event["intent"] == TEST_EVENT_INTENT:
        print(f"✓ Evento persistido: {last_event['intent']} → {last_event['outcome']}")
    else:
        print(f"❌ FALLO: Evento perdido")
        return False
    
    print("\n" + "=" * 60)
    print("✅ TEST DE AMNESIA: APROBADO")
    print("   La memoria ODI sobrevive reinicios.")
    print("   PR-V2.0 Etapa 0 certificada.")
    print("=" * 60)
    
    # Limpiar datos de prueba
    mem.delete_user(TEST_USER)
    print("\n🧹 Datos de prueba eliminados.")
    
    return True


def show_status():
    """Muestra estado actual de la memoria."""
    print("=" * 60)
    print("ODI MEMORIA L1 — ESTADO ACTUAL")
    print("=" * 60)
    
    mem = get_memory()
    
    print(f"Archivo: {mem.path}")
    print(f"Existe: {os.path.exists(mem.path)}")
    print(f"Versión: {mem.data.get('version', 'N/A')}")
    print(f"Creado: {mem.data.get('created_at', 'N/A')}")
    print(f"Actualizado: {mem.data.get('last_updated', 'N/A')}")
    print(f"Usuarios: {len(mem.data.get('users', {}))}")
    print(f"\nSystem flags:")
    for k, v in mem.data.get("system", {}).items():
        print(f"  - {k}: {v}")


def main():
    if len(sys.argv) < 2:
        print("USO:")
        print("  python test_amnesia.py --setup   # Fase 1: Escribir datos")
        print("  python test_amnesia.py --verify  # Fase 2: Verificar persistencia")
        print("  python test_amnesia.py --status  # Ver estado actual")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "--setup":
        setup_test()
    elif command == "--verify":
        success = verify_test()
        sys.exit(0 if success else 1)
    elif command == "--status":
        show_status()
    else:
        print(f"Comando desconocido: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
