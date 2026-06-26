# 🚀 Guía paso a paso (versión fácil)

Esta guía te lleva de cero a tener la demo **funcionando y en internet**, explicado
con palabras simples. No necesitás ser experto. Seguí los pasos en orden.

> **¿Qué es esto?** Un chatbot de demostración que sirve para mostrar cómo
> **Trend Micro AI Guard** protege a una IA de ataques (robo de instrucciones,
> fuga de datos, jailbreaks). Tiene un botón para prender/apagar la protección y
> ver la diferencia en vivo.

---

## 📋 Antes de empezar (lo único que necesitás)

| Para correrlo en tu compu | Para subirlo a un repositorio | Para ponerlo en internet |
|---|---|---|
| **Python 3.9 o superior** | Una cuenta de **GitHub** (o GitLab) | **Docker** instalado |
| Una terminal (Terminal / CMD) | **Git** instalado | (o una cuenta en la nube: AWS, etc.) |

> 💡 ¿No sabés si tenés Python? Abrí la terminal y escribí `python3 --version`.
> Si te muestra un número como `3.11.x`, ya estás listo.

---

## PARTE 1 · Hacerlo funcionar en tu computadora (5 minutos)

### Paso 1 — Entrar a la carpeta del proyecto
Abrí la terminal y andá a la carpeta donde está el proyecto:

```bash
cd ai-guard-demo
```

### Paso 2 — Preparar todo (una sola vez)
Este comando crea el entorno e instala lo necesario, solo. No tenés que tocar nada:

```bash
./setup.sh
```

Vas a ver mensajes con ✓ verdes. Cuando termine, dirá **"Setup completo"**.

> 🔧 Si te dice "permission denied", corré primero: `chmod +x setup.sh run.sh`

### Paso 3 — Arrancar la demo

```bash
./run.sh
```

La terminal te va a mostrar las direcciones. **Dejala abierta** (si la cerrás, se apaga).

### Paso 4 — Abrir en el navegador
Entrá a:

```
http://localhost:8000
```

🎉 ¡Listo! Ya tenés el chatbot corriendo.

> **Importante:** funciona **sin necesidad de claves ni cuentas**. Arranca en
> modo "MOCK" (simulado) que alcanza perfecto para mostrar la demo.

---

## PARTE 2 · Cómo hacer la demostración (lo divertido)

La demo se cuenta en 3 momentos:

**1. Sin protección 😈** — Dejá el botón **"AI Guard" en OFF**. Tocá los atajos
   *"Prompt injection"*, *"Data exfiltration"* y *"Jailbreak"*. El bot cae en
   todas las trampas y "filtra" datos (son datos falsos, inventados para la demo).

**2. Con protección 🛡️** — Prendé el botón **"AI Guard" (ON)**. El header se pone
   verde. Repetí los mismos ataques: ahora aparece el cartel **"AI GUARD · BLOCK"**
   explicando por qué se bloqueó.

**3. La charla normal sigue andando** — Escribí algo normal como
   *"Hola, ¿qué servicios ofrecen?"* y verás que responde sin problema.

👉 Esa es la idea central: **mismo bot, misma pregunta, resultado distinto** según
si AI Guard está prendido o apagado.

---

## PARTE 3 · Subirlo a un repositorio (GitHub)

### Paso 1 — Crear el repositorio vacío
Entrá a GitHub → botón **"New"** → ponele un nombre (ej. `ai-guard-demo`) →
**no** marques "Add README" → **Create repository**.

### Paso 2 — Conectar tu carpeta y subir
Desde la carpeta del proyecto, copiá y pegá esto (cambiá `TU-USUARIO`):

```bash
git init
git add .
git commit -m "Primera versión de AI Guard Demo"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/ai-guard-demo.git
git push -u origin main
```

✅ ¡Listo! Tu código ya está en GitHub.

> 🔒 **Tranquilo con los secretos:** el archivo `.gitignore` ya está configurado
> para que tu `.env` (donde van las claves) **nunca** se suba por accidente.

---

## PARTE 4 · Ponerlo en internet (elegí UNA opción)

### Opción A — La más fácil: con Docker (en cualquier servidor)
Si tenés Docker, son dos comandos:

```bash
docker build -t ai-guard-demo .
docker run -p 8000:8000 ai-guard-demo
```

Y ya está sirviendo en el puerto 8000. Esto funciona igual en tu compu, en un
servidor propio, o en cualquier máquina con Docker.

### Opción B — En la nube AWS (para algo más serio)
La forma recomendada y simple para una demo es:

```
Internet → CloudFront → ALB → ECS Fargate (1 contenedor con esta imagen)
```

Pasos en simple:
1. Subí la imagen de Docker a **Amazon ECR** (el "almacén" de imágenes de AWS).
2. Creá un servicio en **ECS Fargate** que use esa imagen (1 tarea alcanza).
3. Poné un **balanceador (ALB)** adelante para recibir el tráfico.
4. Agregá **CloudFront + certificado** si querés HTTPS y un dominio lindo.

> 📄 En el `README.md` está el detalle de variables de entorno y red para AWS.

---

## 🔑 (Opcional) Usar la API REAL de Trend Micro

Por defecto la demo usa el modo simulado. Si querés conectarla a la API real:

1. Copiá el archivo de ejemplo (si aún no lo hiciste, `setup.sh` ya lo hace):
   ```bash
   cp .env.example .env
   ```
2. Abrí el archivo `.env` con cualquier editor de texto.
3. Pegá tu clave en `TREND_API_KEY=` y verificá que `TREND_GUARD_ENDPOINT`
   apunte a **tu región** (mirá los ejemplos comentados dentro del archivo).
4. Volvé a arrancar con `./run.sh`. Al iniciar dirá *"modo TREND-MICRO"*.

---

## 🆘 Si algo sale mal

| Lo que ves | Por qué pasa | Cómo se arregla |
|---|---|---|
| `permission denied` al correr `./setup.sh` | El archivo no tiene permiso de ejecución | `chmod +x setup.sh run.sh` |
| `python3: command not found` | No tenés Python instalado | Instalá **Python 3.9 o superior** |
| La página da error 404 | Falta la carpeta `frontend/` | Volvé a descomprimir el proyecto completo |
| AI Guard nunca bloquea nada | Estás en modo simulado y el texto no coincide | Usá los **atajos** del panel (ya traen ataques listos) |
| Se apaga solo | Cerraste la terminal donde corría `./run.sh` | Volvé a correr `./run.sh` y dejá la ventana abierta |

---

## 🗺️ Resumen ultra-rápido

```bash
cd ai-guard-demo     # 1. entrar a la carpeta
./setup.sh           # 2. preparar (una vez)
./run.sh             # 3. arrancar
# 4. abrir http://localhost:8000 en el navegador
```

Eso es todo. ¡A disfrutar la demo! 🎬
