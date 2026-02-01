import os
from openai import OpenAI

print("--- DIAGNÓSTICO DE CONEXIÓN IA ---")

# 1. Verificar Key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR FATAL: No se encontró la variable de entorno OPENAI_API_KEY.")
    print("   Solución: Ejecuta 'set OPENAI_API_KEY=sk-...' en la consola antes de correr el script.")
    exit()

print(f"✅ API Key detectada: {api_key[:5]}...{api_key[-4:]}")

# 2. Prueba Real
client = OpenAI(api_key=api_key)

try:
    print("📡 Enviando prueba a OpenAI...")
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Di 'Hola Mundo' si me escuchas."}],
        max_tokens=10
    )
    print(f"✅ RESPUESTA RECIBIDA: {resp.choices[0].message.content}")
    print("--> TU SISTEMA ESTÁ LISTO. EL PROBLEMA ERA DE CONFIGURACIÓN.")
    
except Exception as e:
    print(f"❌ ERROR DE CONEXIÓN CON OPENAI:\n{e}")