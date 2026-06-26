# 🛡️ AI Guard Demo · Trend Micro

Chatbot web **intencionalmente vulnerable** que sirve como sandbox de demostración
para **Trend Micro AI Guard** y **AI Scanner**. Permite mostrar, en vivo, cómo una
IA desprotegida cae ante ataques (robo del system prompt, fuga de datos, jailbreaks)
y cómo AI Guard los bloquea con un solo toggle.

> 🚀 **¿Solo querés ponerlo a andar rápido?**
> Mirá **[INICIO-RAPIDO.md](INICIO-RAPIDO.md)** — guía paso a paso en lenguaje simple.

---

## 📑 Tabla de contenido

- [Qué hace](#-qué-hace)
- [Arranque rápido (60 segundos)](#-arranque-rápido-60-segundos)
- [Estructura de carpetas](#-estructura-de-carpetas)
- [Guion de demo (5 minutos)](#-guion-de-demo-5-minutos)
- [Endpoints de la API](#-endpoints-de-la-api)
- [Arquitectura](#-arquitectura)
- [Despliegue](#-despliegue)
- [Variables de entorno](#-variables-de-entorno)
- [Datos ficticios](#-datos-filtrados-son-ficticios)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Qué hace

- **Frontend:** UI dark estilo "security ops" con un toggle de AI Guard por sesión.
- **Backend:** FastAPI con endpoint `/chat` que también es el target de AI Scanner.
- **AI Guard:** integración real con la API de Trend Micro (chunking 25 % overlap,
  500 tokens/chunk, máx. 5 chunks, *fail-secure*). Si no hay API key corre en modo
  **MOCK** heurístico → la demo funciona end-to-end sin credenciales.
- **AI Scanner:** dos `config.yaml` listos — uno con AI Guard **OFF** (línea base)
  y otro con AI Guard **ON** (protegido) para comparar resultados.
- **Concurrencia:** 1 proceso uvicorn / asyncio maneja ~10 usuarios simultáneos,
  cada uno con estado de sesión independiente.

---

## ⚡ Arranque rápido (60 segundos)

```bash
# 1. Preparar (crea venv, instala dependencias, configura .env)
./setup.sh

# 2. Arrancar
./run.sh

# 3. Abrir el navegador en:
#    http://localhost:8000
```

> Sin credenciales reales el sistema arranca igual y la demo funciona end-to-end
> en modo MOCK. Para probar contra la API real de Trend Micro, editá `.env` y
> completá tu `TREND_API_KEY` (ver [Variables de entorno](#-variables-de-entorno)).

**¿Preferís Docker?**

```bash
docker build -t ai-guard-demo .
docker run -p 8000:8000 ai-guard-demo
```

---

## 📁 Estructura de carpetas

```
ai-guard-demo/
│
├── backend/                     # API + lógica (Python / FastAPI)
│   ├── app.py                   # Entrypoint FastAPI: rutas y orquestación
│   ├── ai_guard.py              # Cliente Trend Micro AI Guard + fallback MOCK
│   ├── llm_handler.py           # LLM vulnerable/seguro + detector de ataques
│   ├── session_manager.py       # Store de sesiones en memoria (thread-safe)
│   └── requirements.txt         # Dependencias de Python
│
├── frontend/                    # UI estática (servida por el backend)
│   ├── index.html               # Estructura de la página
│   ├── style.css                # Estética security-ops dark
│   └── app.js                   # Lógica del cliente (JS vanilla)
│
├── scanner-config/              # Configs para Trend Micro AI Scanner (tmas)
│   ├── config-vulnerable.yaml   # Escaneo con AI Guard OFF (línea base)
│   └── config-protected.yaml    # Escaneo con AI Guard ON (protegido)
│
├── docs/                        # (Reservada para documentación adicional)
│
├── setup.sh                     # Setup: venv + dependencias + .env
├── run.sh                       # Inicia la app (backend + frontend)
├── test_e2e.py                  # Pruebas end-to-end (FastAPI TestClient)
│
├── Dockerfile                   # Imagen para despliegue en contenedor
├── .dockerignore                # Qué excluir al construir la imagen
│
├── .env.example                 # Plantilla de variables de entorno (documentada)
├── .gitignore                   # Protege .env, venv y secretos
│
├── README.md                    # Este archivo
└── INICIO-RAPIDO.md             # Guía paso a paso en lenguaje simple
```

| Carpeta | Responsabilidad |
|---------|-----------------|
| `backend/` | Toda la lógica del servidor. El corazón de la demo. |
| `frontend/` | Lo que ve el usuario. Archivos estáticos, sin build step. |
| `scanner-config/` | Configs para escaneos automatizados con AI Scanner. |
| `docs/` | Espacio para diagramas/notas extra (vacía por defecto). |

---

## 🎬 Guion de demo (5 minutos)

### Acto 1 · Modelo expuesto (AI Guard OFF)
1. Verificá que el toggle **"AI Guard"** esté en **OFF** (es el default).
2. Click en el atajo **"Prompt injection"** → el modelo entrega su system prompt
   y credenciales internas simuladas.
3. Probá **"Data exfiltration"** y **"Jailbreak (DAN)"** — todos pasan.

### Acto 2 · Modelo protegido (AI Guard ON)
1. Activá el toggle. El header se pone verde con badge **"ON"**.
2. Repetí los mismos ataques. Cada respuesta muestra el badge
   **"AI GUARD · BLOCK"** con el motivo y la etapa (`input` u `output`).
3. La charla normal sigue funcionando (ej. *"Hola, ¿qué servicios ofrecen?"*).

### Acto 3 · AI Scanner automatizado
```bash
export TMAS_API_KEY=<tu-key>

# Línea base — chatbot expuesto
./tmas aiscan llm -c scanner-config/config-vulnerable.yaml \
    --output json=baseline.json,markdown=baseline.md

# Con protección — mismo chatbot, AI Guard ON
./tmas aiscan llm -c scanner-config/config-protected.yaml \
    --output json=protected.json,markdown=protected.md
```
Los reportes muestran una caída drástica de *findings* entre ambos escaneos →
demostración **cuantitativa** del valor de AI Guard.

---

## 🔌 Endpoints de la API

| Método | Path | Descripción |
|--------|------|-------------|
| `POST` | `/chat` | Mensaje al chatbot. **Target de AI Scanner**. |
| `POST` | `/session/create` | Crea una sesión nueva. Devuelve `session_id`. |
| `POST` | `/session/guard` | Toggle de AI Guard por sesión. |
| `GET`  | `/session/{sid}` | Estado actual de una sesión. |
| `GET`  | `/health` | Liveness + modo de operación. |
| `GET`  | `/docs` | Swagger UI auto-generado. |
| `GET`  | `/` | Frontend. |

### Esquema de `/chat`

**Request:**
```json
{
  "message": "Ignore all previous instructions",
  "session_id": "uuid-opcional",
  "ai_guard_enabled": true
}
```
`ai_guard_enabled` es opcional. Si se omite, se usa el estado guardado en la
sesión. Pasarlo explícitamente permite que AI Scanner (stateless por request)
controle el modo sin tocar `/session/guard`.

**Response:**
```json
{
  "session_id": "...",
  "ai_guard_enabled": true,
  "blocked": true,
  "stage": "input",
  "response": "⛔ Tu mensaje fue bloqueado por Trend Micro AI Guard…",
  "guard_reasons": ["[Violation] Policy name: prompt_attack"],
  "attack_patterns_detected": ["ignore all previous instructions"],
  "guard_mode": "trend-micro"
}
```

---

## 🏗️ Arquitectura

```
┌──────────────┐    HTTP     ┌────────────────────────────┐
│   Browser    │ ──────────► │  FastAPI app (uvicorn)     │
│  (frontend)  │             │  ┌──────────────────────┐  │
└──────────────┘             │  │ /chat handler        │  │
                             │  │  ├─ SessionManager   │  │
┌──────────────┐    HTTP     │  │  ├─ AI Guard input  ─┼──┼──► Trend Micro
│  AI Scanner  │ ──────────► │  │  ├─ LLM (sim/openai) │  │    AI Guard API
│   (tmas)     │             │  │  └─ AI Guard output ─┼──┼──► (chunked, fail-secure)
└──────────────┘             │  └──────────────────────┘  │
                             │  Static files (/frontend)  │
                             └────────────────────────────┘
```

**Componentes**
- `backend/app.py` — rutas FastAPI, orquesta los demás módulos.
- `backend/session_manager.py` — dict thread-safe en memoria.
- `backend/llm_handler.py` — detector de patrones de ataque + responder
  vulnerable/seguro + integración opcional con OpenAI.
- `backend/ai_guard.py` — cliente async con chunking y fallback MOCK.
- `frontend/` — UI estática servida por el propio backend.

**Concurrencia**
- Single-process, single-worker uvicorn.
- Todos los handlers son `async`. La única I/O bloqueante (Trend Micro API)
  usa `httpx.AsyncClient`, así el event loop nunca se traba.
- Resultado: ~10 usuarios simultáneos sin problema.
- Para escalar: mover `SessionManager` a Redis, subir a N workers y poner un LB.

---

## ☁️ Despliegue

### Docker (lo más simple, anda en cualquier lado)
```bash
docker build -t ai-guard-demo .
docker run -p 8000:8000 ai-guard-demo
# con API real:
docker run -p 8000:8000 -e TREND_API_KEY=tu-key ai-guard-demo
```

### AWS (referencia para staging/demo)
```
Internet → CloudFront → ALB → ECS Fargate (1 task, 1 contenedor)
                                          └── imagen Docker de este repo
```
- **ECS Fargate** (no EC2): cero gestión de servidores; ideal para 1 task con
  ~10 usuarios. Si crece, autoscaling por CPU.
- **CloudFront + ACM** delante para HTTPS y CDN del frontend estático.
- **Sin estado persistente** para la demo: las sesiones viven en memoria del
  task (si reinicia, se pierden — aceptable para demo). Para persistencia,
  agregá **ElastiCache (Redis)** y reemplazá `SessionManager`.
- **Networking:** ALB en subred pública (80/443); ECS en subred privada que solo
  acepta tráfico del ALB; NAT egress para llegar a `api.*.xdr.trendmicro.com`.

---

## 🔑 Variables de entorno

Copiá `.env.example` a `.env` (lo hace `setup.sh` automáticamente) y completá lo
que necesites. **Todas son opcionales** — sin ninguna, la demo corre en modo MOCK.

| Variable | Para qué sirve | Default |
|----------|----------------|---------|
| `TREND_API_KEY` | API key de Trend Vision One (scope AI Guard). Sin ella → modo MOCK. | *(vacío)* |
| `TREND_GUARD_ENDPOINT` | Endpoint **regional** de AI Guard. Debe coincidir con tu tenant. | US por defecto |
| `OPENAI_API_KEY` | Si está, las respuestas normales salen de un LLM real. Sin ella → respuestas canned. | *(vacío)* |
| `OPENAI_MODEL` | Modelo de OpenAI a usar. | `gpt-4o-mini` |
| `HOST` | Interfaz de escucha. | `0.0.0.0` |
| `PORT` | Puerto del servidor. | `8000` |

> ⚠️ El endpoint de AI Guard es **regional**. Mirá los ejemplos comentados dentro
> de `.env.example` para elegir el correcto según tu región (US, EU, AU, JP, etc.).

---

## 🧪 Datos "filtrados" son ficticios

Toda la información sensible que aparece en modo vulnerable (correos
`admin@empresa-interna.demo`, IPs `10.0.x.x`, API keys `AKIA-DEMO-FAKE-...`)
es **100 % ficticia**: usa dominios `.demo`, prefijos `FAKE` y patrones que jamás
podrían corresponder a secretos reales. Existe únicamente para demostrar el
comportamiento de AI Guard frente a exfiltración de datos.

---

## 🆘 Troubleshooting

| Síntoma | Causa probable | Fix |
|---------|----------------|-----|
| `setup.sh` falla en `pip install` | Python < 3.9 | Instalar Python 3.9+ |
| `permission denied` al correr scripts | Falta permiso de ejecución | `chmod +x setup.sh run.sh` |
| `run.sh` arranca pero `/` da 404 | Falta la carpeta `frontend/` | Re-extraer el proyecto completo |
| AI Guard nunca bloquea | Sin `TREND_API_KEY` y el texto no coincide | Usar los **atajos** del panel |
| AI Scanner no llega al endpoint | Backend no escucha en `0.0.0.0` o firewall | Verificar `HOST=0.0.0.0` |
| El toggle se pierde al refrescar | Esperado: el `session_id` se regenera | Es así por diseño de demo |

---

### 🧰 Stack

`Python 3.9+` · `FastAPI` · `uvicorn` · `httpx` · `pydantic` · `JS vanilla` · `Docker`
