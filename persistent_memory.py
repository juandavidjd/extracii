"""
ODI — Hipocampo Operativo (Memoria Nivel 1)
============================================
Versión: 1.0
Fecha: 2026-01-12
Cumple: RA-ODI, CA-V2.0, PR-V2.0

Principios:
- Determinista (sin emoción, sin reasoning)
- Escritura atómica (tmp → rename)
- Persistente (sobrevive reinicios)
- Soberano (datos locales, exportables)
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, Any, Optional

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

MEMORY_PATH = os.environ.get("ODI_MEMORY_PATH", "/app/data/memory_L1.json")
BACKUP_DIR = os.environ.get("ODI_BACKUP_DIR", "/app/data/backups")
MAX_EVENTS = 20
MAX_BACKUPS = 3


class PersistentMemoryL1:
    """
    Hipocampo Operativo ODI.
    
    Almacena:
    - Hechos estables (facts)
    - Estados binarios (flags)
    - Eventos operativos (events)
    
    NO almacena:
    - Emoción
    - Razonamiento
    - Conversación
    """

    def __init__(self, path: str = MEMORY_PATH):
        self.path = path
        self._ensure_directories()
        self.data = self._load()

    # ─────────────────────────────────────────────────────────────
    # INICIALIZACIÓN
    # ─────────────────────────────────────────────────────────────

    def _ensure_directories(self):
        """Crea directorios si no existen."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        """
        Carga segura con fallback a estructura base.
        Si el archivo está corrupto, intenta restaurar desde backup.
        """
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Validar estructura mínima
                    if "version" in data and "users" in data:
                        return data
            except (json.JSONDecodeError, IOError):
                # Intentar restaurar desde backup
                restored = self._restore_from_backup()
                if restored:
                    return restored

        # Estructura base inmutable
        return {
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "users": {},
            "system": {
                "linux_migrated": True,
                "whatsapp_enabled": False,
                "m6_fitment_enabled": False
            }
        }

    # ─────────────────────────────────────────────────────────────
    # PERSISTENCIA (CA-V2.0)
    # ─────────────────────────────────────────────────────────────

    def _save(self):
        """
        Escritura Atómica: tmp → rename
        Garantiza integridad ante cortes de energía.
        """
        self.data["last_updated"] = datetime.utcnow().isoformat()
        
        tmp_path = f"{self.path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.path)
        except IOError as e:
            # Limpiar archivo temporal si falló
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise e

    def _create_backup(self):
        """Crea backup rotativo (máximo 3)."""
        if not os.path.exists(self.path):
            return
            
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"memory_L1_{timestamp}.bak")
        
        shutil.copy2(self.path, backup_path)
        
        # Rotación: eliminar backups antiguos
        backups = sorted([
            f for f in os.listdir(BACKUP_DIR) 
            if f.startswith("memory_L1_") and f.endswith(".bak")
        ])
        
        while len(backups) > MAX_BACKUPS:
            oldest = backups.pop(0)
            os.remove(os.path.join(BACKUP_DIR, oldest))

    def _restore_from_backup(self) -> Optional[Dict[str, Any]]:
        """Intenta restaurar desde el backup más reciente."""
        if not os.path.exists(BACKUP_DIR):
            return None
            
        backups = sorted([
            f for f in os.listdir(BACKUP_DIR)
            if f.startswith("memory_L1_") and f.endswith(".bak")
        ], reverse=True)
        
        for backup_file in backups:
            backup_path = os.path.join(BACKUP_DIR, backup_file)
            try:
                with open(backup_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "version" in data and "users" in data:
                        # Restaurar archivo principal
                        shutil.copy2(backup_path, self.path)
                        return data
            except (json.JSONDecodeError, IOError):
                continue
                
        return None

    # ─────────────────────────────────────────────────────────────
    # USUARIOS
    # ─────────────────────────────────────────────────────────────

    def ensure_user(self, user_id: str):
        """Garantiza existencia del nodo de usuario."""
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "first_seen": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat(),
                "facts": {},
                "flags": {},
                "events": []
            }
            self._save()
        else:
            # Actualizar last_seen
            self.data["users"][user_id]["last_seen"] = datetime.utcnow().isoformat()

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos de usuario sin crear si no existe."""
        return self.data["users"].get(user_id)

    def user_exists(self, user_id: str) -> bool:
        """Verifica si el usuario existe."""
        return user_id in self.data["users"]

    # ─────────────────────────────────────────────────────────────
    # FACTS (Hechos Estables)
    # ─────────────────────────────────────────────────────────────

    def set_fact(self, user_id: str, key: str, value: Any):
        """
        Almacena hecho estable.
        Ejemplos: business_name, industry, preferred_channel
        """
        self.ensure_user(user_id)
        self.data["users"][user_id]["facts"][key] = value
        self._save()

    def get_fact(self, user_id: str, key: str, default: Any = None) -> Any:
        """Obtiene hecho específico."""
        user = self.get_user(user_id)
        if user:
            return user["facts"].get(key, default)
        return default

    def remove_fact(self, user_id: str, key: str):
        """Elimina un hecho."""
        if user_id in self.data["users"]:
            self.data["users"][user_id]["facts"].pop(key, None)
            self._save()

    # ─────────────────────────────────────────────────────────────
    # FLAGS (Estados Binarios)
    # ─────────────────────────────────────────────────────────────

    def set_flag(self, user_id: str, flag: str, value: bool):
        """
        Establece estado binario.
        Ejemplos: whatsapp_verified, onboarding_complete
        """
        self.ensure_user(user_id)
        self.data["users"][user_id]["flags"][flag] = value
        self._save()

    def get_flag(self, user_id: str, flag: str, default: bool = False) -> bool:
        """Obtiene flag específico."""
        user = self.get_user(user_id)
        if user:
            return user["flags"].get(flag, default)
        return default

    # ─────────────────────────────────────────────────────────────
    # EVENTS (Eventos Operativos)
    # ─────────────────────────────────────────────────────────────

    def add_event(self, user_id: str, intent: str, outcome: str):
        """
        Registra evento operativo.
        Mantiene máximo 20 eventos (anti-crecimiento exponencial).
        
        Args:
            intent: Tipo de intención (OMA Átomo 3)
            outcome: Resultado (OMA Átomo 5: SUCCESS, PENDING_HUMAN, etc.)
        """
        self.ensure_user(user_id)
        
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "intent": intent,
            "outcome": outcome
        }
        
        events = self.data["users"][user_id]["events"]
        events.append(event)
        
        # Límite estricto
        while len(events) > MAX_EVENTS:
            events.pop(0)
        
        self._save()

    def get_last_event(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el último evento del usuario."""
        user = self.get_user(user_id)
        if user and user["events"]:
            return user["events"][-1]
        return None

    def get_events(self, user_id: str, limit: int = 5) -> list:
        """Obtiene los últimos N eventos."""
        user = self.get_user(user_id)
        if user:
            return user["events"][-limit:]
        return []

    # ─────────────────────────────────────────────────────────────
    # SYSTEM FLAGS
    # ─────────────────────────────────────────────────────────────

    def set_system_flag(self, flag: str, value: bool):
        """Establece flag del sistema."""
        self.data["system"][flag] = value
        self._save()

    def get_system_flag(self, flag: str, default: bool = False) -> bool:
        """Obtiene flag del sistema."""
        return self.data["system"].get(flag, default)

    # ─────────────────────────────────────────────────────────────
    # SNAPSHOT (Para inyección en prompt/canales)
    # ─────────────────────────────────────────────────────────────

    def snapshot(self, user_id: str) -> Dict[str, Any]:
        """
        Devuelve estado completo del usuario para inyección contextual.
        Usado por: voz, WhatsApp, n8n
        """
        self.ensure_user(user_id)
        return {
            "user": self.data["users"][user_id],
            "system": self.data["system"]
        }

    def snapshot_for_prompt(self, user_id: str) -> str:
        """
        Genera bloque de texto para inyectar en system prompt.
        Formato estructurado, no conversacional.
        """
        self.ensure_user(user_id)
        user = self.data["users"][user_id]
        
        lines = ["[SYSTEM_MEMORY_L1]"]
        
        # Facts
        if user["facts"]:
            lines.append("User Facts:")
            for k, v in user["facts"].items():
                lines.append(f"  - {k}: {v}")
        
        # Flags
        active_flags = [k for k, v in user["flags"].items() if v]
        if active_flags:
            lines.append(f"Active Flags: {', '.join(active_flags)}")
        
        # System
        lines.append("System:")
        lines.append(f"  - linux_migrated: {self.data['system'].get('linux_migrated', False)}")
        lines.append(f"  - whatsapp_enabled: {self.data['system'].get('whatsapp_enabled', False)}")
        
        lines.append("[/SYSTEM_MEMORY_L1]")
        
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────
    # SOBERANÍA (MEO Pilar 1)
    # ─────────────────────────────────────────────────────────────

    def export_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Exporta datos de usuario en formato universal.
        Cumple: Derecho a irse (MEO Pilar 1)
        """
        user = self.get_user(user_id)
        if not user:
            return None
            
        return {
            "export_timestamp": datetime.utcnow().isoformat(),
            "format_version": "1.0",
            "user_id": user_id,
            "data": user
        }

    def delete_user(self, user_id: str) -> bool:
        """
        Elimina usuario completamente (hard delete).
        Cumple: Kill Switch (MEO Pilar 1)
        """
        if user_id in self.data["users"]:
            # Backup antes de eliminar
            self._create_backup()
            del self.data["users"][user_id]
            self._save()
            return True
        return False

    def backup_now(self):
        """Fuerza creación de backup inmediato."""
        self._create_backup()


# ═══════════════════════════════════════════════════════════════
# SINGLETON PARA USO GLOBAL
# ═══════════════════════════════════════════════════════════════

_memory_instance: Optional[PersistentMemoryL1] = None

def get_memory() -> PersistentMemoryL1:
    """Obtiene instancia singleton de memoria."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = PersistentMemoryL1()
    return _memory_instance


# ═══════════════════════════════════════════════════════════════
# HELPERS RÁPIDOS
# ═══════════════════════════════════════════════════════════════

def read_memory(user_id: str) -> Dict[str, Any]:
    """Helper: Lee snapshot de usuario."""
    return get_memory().snapshot(user_id)

def write_fact(user_id: str, key: str, value: Any):
    """Helper: Escribe hecho."""
    get_memory().set_fact(user_id, key, value)

def write_flag(user_id: str, flag: str, value: bool):
    """Helper: Escribe flag."""
    get_memory().set_flag(user_id, flag, value)

def log_event(user_id: str, intent: str, outcome: str):
    """Helper: Registra evento."""
    get_memory().add_event(user_id, intent, outcome)
