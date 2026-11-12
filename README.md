# Sistema de Control Presupuestario y Ejecución Financiera

Aplicación web que importa el Excel del sistema contable (`RETO 1.xlsx`), almacena la información en una base
relacional y reproduce los siete reportes del reto con filtros combinados, desglose por niveles y exportación a
Excel y PDF.

- **Backend:** Python · FastAPI · SQLAlchemy 2 · pandas/openpyxl · ReportLab
- **Frontend:** React 18 · Vite · TypeScript · Tailwind CSS · Recharts · TanStack Table · Lucide
- **Base de datos:** SQLite por defecto (cero configuración) · PostgreSQL cambiando `DATABASE_URL`

---

## 0. Inicio con un clic (recomendado)

| Sistema | Solo esta red (Wi-Fi) | Enlace para cualquier lugar (internet) |
|---|---|---|
| Windows | doble clic en `INICIAR.bat` | doble clic en `INICIAR-CON-INTERNET.bat` |
| macOS | doble clic en `INICIAR.command` (la 1.ª vez: clic derecho › Abrir) | `INICIAR-CON-INTERNET.command` |
| Linux | `./iniciar.sh` | `./iniciar.sh --internet` |

Requisitos de la computadora: **Python 3.11+** (en Windows marque «Add python.exe to PATH»). **Node.js LTS** solo
hace falta si `frontend/dist` no existe o cambió el código; al copiar la carpeta a otra PC con `frontend/dist` ya
compilado, basta Python. La primera ejecución necesita internet para descargar dependencias.

El archivo instala lo que falte, compila la página, la sirve junto con la API en un solo puerto (8000) y abre el
navegador. Los enlaces aparecen en la ventana y en `ENLACES.txt`. Con la opción de internet se descarga
Cloudflare Tunnel (gratuito, sin cuenta) y se obtiene un enlace `https://….trycloudflare.com` que funciona desde
cualquier red. Ese enlace **cambia en cada inicio** y solo funciona mientras la computadora esté encendida con la
ventana abierta. Antes de compartirlo, asegúrese de que la contraseña de `admin` sea robusta.

## 1. Puesta en marcha (manual, para desarrollo)

Requisitos: Python 3.11+ y Node.js 18+.

### Backend (terminal 1)

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate        Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

En el **primer arranque** se crea el usuario `admin`. Si no definió `ADMIN_PASSWORD`, la contraseña se genera al
azar y se muestra en la consola y en `data/credenciales_iniciales.txt`. Para fijarla, copie `.env.example` a `.env`
(en la raíz del proyecto) y defina `ADMIN_PASSWORD` **antes** del primer arranque.

Documentación interactiva de la API: <http://localhost:8000/docs>

### Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Abrir <http://localhost:5173>. Vite redirige `/api` al backend en el puerto 8000.

### Alternativa: un solo puerto

```bash
cd frontend && npm install && npm run build
cd ../backend && uvicorn app.main:app --port 8000     # sirve también la interfaz en http://localhost:8000
```

### Acceso desde otros dispositivos de la misma red (Wi-Fi)

El frontend llama siempre a `/api` (ruta relativa) y Vite reenvía esas llamadas al backend del equipo anfitrión, por
lo que el teléfono o la otra laptop **nunca** usan su propio `localhost`. No hay IPs escritas en el código.

1. En el equipo anfitrión, arranque el backend como siempre (`uvicorn app.main:app --reload --port 8000`) y el
   frontend con `npm run dev`. Vite ya escucha en `0.0.0.0` (toda la red local) y muestra la línea
   `Network: http://192.168.x.x:5173`.
2. Si no la ve, busque la IP local del anfitrión:
   - Windows: `ipconfig` → «Dirección IPv4» del adaptador Wi-Fi.
   - macOS: `ipconfig getifaddr en0` · Linux: `hostname -I`.
3. En el teléfono u otra computadora conectada **al mismo Wi-Fi**, abra `http://IP-DEL-ANFITRIÓN:5173`.

Modo de un solo puerto (sin Vite): `npm run build` y luego `uvicorn app.main:app --host 0.0.0.0 --port 8000`;
desde otros equipos se abre `http://IP-DEL-ANFITRIÓN:8000`.

**Qué hace el iniciador para que otros dispositivos puedan entrar** (comprobado en cada arranque):

1. **Firewall de Windows** — causa más frecuente. Si al primer arranque se canceló el aviso «¿Permitir a Python…?»,
   Windows crea una regla que *bloquea* a Python, y un bloqueo gana a cualquier permiso. El iniciador lo detecta,
   pide permiso de administrador **una sola vez** (pulse «Sí»), elimina esos bloqueos y abre los puertos
   5173, 4173 y 8000-8019 en redes privadas **y públicas** (las redes de eventos suelen quedar como «Públicas»).
2. **Dirección equivocada** — `localhost` solo sirve en la propia computadora, y los adaptadores virtuales
   (WSL, Hyper-V, VirtualBox, VMware, Docker, VPN) muestran IPs inalcanzables. El iniciador los descarta, muestra
   primero la IP del Wi-Fi real y abre el navegador con esa dirección para que pueda copiarla y compartirla.
3. Muestra una **prueba rápida**: en el otro dispositivo, `http://IP:8000/api/salud` debe mostrar `{"estado":"ok"}`.

**Si aun así no abre:**
- Escriba la dirección completa con `http://` (no `https://`). Si el navegador avisa «conexión no segura», elija continuar.
- Ambos equipos en la **misma** red Wi-Fi (no la de invitados, no datos móviles, sin VPN).
- **Aislamiento de clientes**: muchas redes de invitados, hoteles, universidades y eventos impiden que los
  dispositivos se vean entre sí. Ninguna configuración de la computadora lo resuelve: use `INICIAR-CON-INTERNET`
  o un punto de acceso del celular.
- Antivirus con firewall propio (Avast, ESET, Kaspersky, Norton…): permita Python o los puertos 8000-8019.
- macOS: acepte «Permitir conexiones entrantes» para Python. Linux con ufw: `sudo ufw allow 8000:8019/tcp`.

Seguridad: en modo desarrollo el backend sigue escuchando solo en `127.0.0.1` (lo alcanza únicamente el proxy de
Vite); la base de datos SQLite no se expone. CORS acepta `CORS_ORIGENES` y, si `CORS_RED_LOCAL=true` (por defecto),
orígenes de redes privadas (192.168.x.x, 10.x.x.x, 172.16-31.x.x). Para restringir solo al anfitrión use
`VITE_HOST=127.0.0.1` y `CORS_RED_LOCAL=false`. No publique esta configuración en internet sin HTTPS.

### Pruebas automatizadas

```bash
# desde la raíz del proyecto, con el entorno virtual del backend activo
python -m pytest
```

Usan una base SQLite temporal, importan el `data/RETO 1.xlsx` real a través de la API y comparan los resultados
contra la hoja `BD` y contra las tablas dinámicas del propio Excel (31 pruebas).

### PostgreSQL (opcional)

```bash
pip install -r backend/requirements-postgres.txt
# en .env:
DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/presupuesto
```

Las tablas se crean solas al arrancar. **El código es compatible, pero esta entrega solo se ejecutó y probó con
SQLite.**

---

## 1.1 Alertas, análisis y comparación (nuevo)

- **Alertas y seguimiento** (`/seguimiento`): el administrador pulsa «Agregar meta» y elige gestión, qué evaluar
  (presupuesto total, área, financiador, región, rubro o cuenta; uno o todos), mes de evaluación, meta de ejecución
  (%), tolerancia amarilla y umbral rojo (en puntos porcentuales por debajo de la meta) y límite de gasto (% del
  vigente). Las metas se guardan en la tabla `reglas_alerta` y se pueden activar, desactivar, editar o eliminar.
  - `% real = ejecución acumulada hasta el mes ÷ presupuesto vigente de toda la gestión × 100`
  - `desviación = % real − % meta` (puntos porcentuales). Verde: desviación ≥ −tolerancia. Amarillo: entre
    −tolerancia y −umbral rojo. Rojo: más abajo, o gasto por encima del límite (sobreejecución), o gasto sin presupuesto.
  - Sin metas no hay alertas de subejecución: un saldo sin gastar no se considera un problema por sí mismo.
- **Análisis y recomendaciones** (`/analisis`): hallazgos generados con reglas fijas y un análisis por área,
  financiador, región, rubro, cuenta o total con evolución mensual, meta y diferencia cuando existe una meta.
- **Comparar gestiones** (`/comparar`): elige dos gestiones, el mes de corte (igual para ambas) y el desglose.
  Necesita al menos dos gestiones importadas; cada importación queda asociada a su gestión y no reemplaza a otras.
- Endpoints: `GET/POST/PUT/DELETE /api/analitica/reglas`, `GET /api/analitica/seguimiento`, `/analisis`,
  `/comparacion`, `/recomendaciones` (filtros comunes). Pruebas en `tests/test_seguimiento.py`.
- La página anterior «Alertas y proyección» se conserva como «Anomalías y proyección» (`/alertas`).

## 2. Estructura real del Excel

| Hoja | Tipo | Uso |
|---|---|---|
| `BD` | Datos originales (encabezados en fila 2, 3.574 filas) | **Única hoja que se importa** |
| `Rubro`, `por cuenta`, `Financiador`, `Por Area y Fin`, `Por region y Area`, `Por mes` | Tablas dinámicas derivadas de `BD` | Referencia para validar los cálculos |
| `Dashboard` | Vacía | — |
| `Detalle2` | Oculta; detalle de otro corte de datos (otros financiadores, sin columna Cuenta) | No se usa |

La hoja `BD` mezcla tres tipos de fila:

| Tipo de fila | Cómo se reconoce | Filas | `presupuesto Bs` | En el sistema |
|---|---|---|---|---|
| Asignación anual | `mes = PTTO`, `ref = PRESUPUESTO`, sin ejecución | 1.822 (10 sin importe) | 2.532.269,47 | `presupuestos` · origen `ASIGNACION_ANUAL` |
| Presupuesto registrado en un mes | mes Enero–Septiembre, `ref = PRESUPUESTO`, sin ejecución | 274 | 102.415,38 | `presupuestos` · origen `REGISTRO_MENSUAL` |
| Movimiento de ejecución | importe en `Ejecución` | 1.478 | 528.694,16 (igual a su ejecución) | `movimientos` + `presupuestos` · origen `CONTRAPARTE_MOVIMIENTO` |

Dimensiones: 3 financiadores (`fondo`), 2 regiones (LP, SC), 8 áreas, 6 rubros, 25 combinaciones rubro–cuenta con
importe, 9 meses, gestión 2026.

## 3. Reglas financieras (deducidas de las tablas dinámicas)

```
Presupuesto          = Σ «presupuesto Bs» de TODAS las filas      → 3.163.379,01
Modificaciones       = Σ modificaciones registradas en el sistema → 0,00 con el archivo del reto
Presupuesto vigente  = Presupuesto + Modificaciones
Ejecución            = Σ «Ejecución»                              →   528.694,16
Saldo                = Presupuesto vigente − Ejecución            → 2.634.684,85
% de ejecución       = Ejecución ÷ Presupuesto vigente            → 16,71 %
```

- Todas las cifras del archivo están en **bolivianos**. `dsus` es el equivalente en USD de cada movimiento con su
  `tasa` (6,96 de enero a junio; entre 9,78 y 12,58 desde julio). Se conserva el USD del archivo, no se recalcula.
  No existe presupuesto en USD, por lo que no hay selector de moneda: el USD se muestra como columna adicional.
- **Filtro por mes:** se aplica a la fila tal como está en el Excel. Con un mes seleccionado, el presupuesto es el
  registrado en ese mes (igual que la hoja «Por mes»); la asignación anual es el valor `PTTO`. El presupuesto anual
  **no se prorratea** entre meses.

### Supuestos documentados

1. **Modificaciones presupuestarias:** el Excel no las contiene. Se registran desde *Administración* y afectan al
   presupuesto vigente y al saldo.
2. **Gestión:** las filas de presupuesto no tienen fecha; se asignan a la gestión detectada en las fechas de los
   movimientos (2026) o a la que indique el administrador al importar.
3. **`haber` / `hsus`:** están siempre en 0. Se almacenan, pero la ejecución es la columna `Ejecución`, igual que
   en las tablas dinámicas. Si un archivo futuro trae reversiones en `haber`, se advierte en la importación.
4. **Nombres de región:** `LP` = La Paz y `SC` = Santa Cruz (el archivo solo trae la sigla).
5. **Importaciones repetidas:** no se deduplica fila por fila, porque el libro contiene legítimamente filas
   idénticas. Se rechaza el mismo archivo (huella SHA-256) y una gestión solo admite un archivo vigente; para
   actualizarla se usa «Reemplazar datos de la gestión».

### Inconsistencias detectadas en el archivo (se informan al importar; el dato no se altera)

- El rubro **9. Otros Gastos Ope.** no tiene ninguna ejecución (también es así en las tablas dinámicas).
- 10 filas `PTTO` sin importe (se omiten).
- 8 filas con la cuenta bajo un rubro distinto (p. ej. «9.2 Expensas» en rubro 4; «5.2 Viajes Nacionales» en
  rubro 9), una cuenta «9.2» sin nombre y una cuenta que repite el nombre del rubro.
- 2 movimientos de julio (filas 3018 y 3019 de `BD`) cuyo `dsus` no coincide con Ejecución ÷ tasa.
- 144 fechas vienen como fecha de Excel y 1.334 como texto `dd/mm/aaaa`; se leen ambos formatos.

---

## 4. Estado de funcionalidades

**Verificado con pruebas automáticas** (`pytest`, 31 pruebas) **y con un recorrido real en navegador**:

| Funcionalidad | Estado |
|---|---|
| Lectura y validación de `RETO 1.xlsx`, vista previa e importación transaccional | Terminado y verificado |
| Prevención de duplicados, reemplazo de gestión, reversión ante fallo | Terminado y verificado |
| Indicadores del dashboard y 7 gráficos, reactivos a los filtros | Terminado y verificado |
| Reporte 1 · Rubro y cuenta | Terminado · coincide con hojas `Rubro` y `por cuenta` |
| Reporte 2 · Financiador | Terminado · coincide con hoja `Financiador` |
| Reporte 3 · Área y financiador | Terminado · coincide con hoja `Por Area y Fin` |
| Reporte 4 · Región | Terminado · coincide con hoja `Por region y Area` (5 niveles) |
| Reporte 5 · Por mes | Terminado · coincide con hoja `Por mes` |
| Reporte 6 · Detalle de movimientos (búsqueda, fechas, orden, paginación) | Terminado y verificado |
| Reporte 7 · Consolidado | Terminado y verificado |
| Filtros combinados (gestión, mes, financiador, región, área, rubro, cuenta) | Terminado y verificado contra pandas |
| Exportación Excel y PDF de los 7 reportes con los filtros aplicados | Terminado y verificado |
| Inicio de sesión, roles administrador / consulta, endpoints protegidos, auditoría | Terminado y verificado |
| Modificaciones presupuestarias | Terminado y verificado |
| Alertas por umbral, posibles anomalías, proyección de cierre (opcionales) | Terminado; verificación básica |

**Pendiente o no verificado:**

- **PostgreSQL:** soportado por configuración, pero no se ejecutó contra un servidor PostgreSQL.
- **Comparación entre gestiones:** implementada (gráficos y tablas), pero solo hay datos de 2026; no se probó con un
  segundo año real.
- **Filtro de moneda:** no aplica (todo el archivo está en Bs); se muestra el USD como columna.
- **Rango de fechas:** disponible en el detalle de movimientos; en el resto de reportes el filtro temporal es por mes.
- Despliegue en la nube, copias de seguridad, recuperación de contraseña y migraciones (Alembic): fuera del MVP.

---

## 5. API

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/login` · GET `/api/auth/yo` | Sesión (JWT) |
| POST | `/api/importaciones/previsualizar` | Valida el archivo y devuelve el resumen sin guardar |
| POST | `/api/importaciones` | Importa (`archivo`, `gestion` opcional, `reemplazar`) |
| GET | `/api/importaciones` · `/api/importaciones/{id}` | Historial y detalle |
| GET | `/api/filtros` · `/api/gestiones` | Catálogos y resumen por gestión |
| GET | `/api/dashboard/resumen` | Indicadores y series para los gráficos |
| GET | `/api/reportes/rubros` · `financiadores` · `areas-financiadores` · `regiones` | Reportes jerárquicos |
| GET | `/api/reportes/mensuales` · `movimientos` · `consolidado` | Reportes 5, 6 y 7 |
| GET | `/api/reportes/exportar?reporte=…&formato=xlsx\|pdf` | Descarga con los filtros aplicados |
| GET | `/api/analitica/alertas` · `anomalias` · `proyeccion` · GET/PUT `umbrales` | Funciones opcionales |
| GET/POST/PATCH | `/api/usuarios` · GET `/api/auditoria` | Administración |
| GET/POST/DELETE | `/api/modificaciones` · GET `/api/tipos-cambio` | Modificaciones y tipos de cambio |

Filtros comunes (ids separados por coma): `gestion`, `mes` (0 = PTTO), `financiador`, `region`, `area`, `rubro`, `cuenta`.

## 6. Modelo de datos

`roles` · `usuarios` · `gestiones` · `financiadores` · `regiones` · `areas` · `rubros` · `cuentas` (FK a rubro) ·
`importaciones` · `presupuestos` · `modificaciones` · `movimientos` · `tipos_cambio` · `auditoria` · `configuracion`.

Presupuestos, modificaciones y movimientos comparten las claves foráneas `gestion`, `financiador`, `region`, `area`
y `cuenta`. Cada presupuesto y movimiento guarda `importacion_id` y `fila_excel` para rastrear su origen; el archivo
original se conserva en `data/importaciones/`. Importes en `NUMERIC(18,2)` y cálculos en `Decimal`.

## 7. Estructura del proyecto

```
proyecto/
├── backend/
│   ├── app/
│   │   ├── main.py · config.py
│   │   ├── database/   sesión y creación de tablas
│   │   ├── models/     modelo relacional
│   │   ├── schemas/    validaciones Pydantic
│   │   ├── routers/    auth, importaciones, reportes, analitica, admin
│   │   └── services/   excel_parser, importador, reportes, exportar, analitica, seguridad
│   └── requirements.txt
├── frontend/src/       components · pages · hooks · services · types
├── data/               RETO 1.xlsx (referencia) y base SQLite
├── tests/              validación financiera, importación, seguridad y exportación
├── .env.example
└── README.md
```

---

## 8. Guion de demostración para el jurado (≈ 6 minutos)

1. **Inicio de sesión** como administrador. El dashboard aparece vacío con el acceso a «Importar datos».
2. **Importar datos:** seleccionar `RETO 1.xlsx` → «Validar y ver resumen». Mostrar que el sistema reconoce la hoja
   `BD`, clasifica las demás como reportes derivados y detecta 3.574 filas, 1.478 movimientos y las advertencias.
   Confirmar. Intentar importarlo otra vez para mostrar que **no duplica**.
3. **Dashboard:** presupuesto 3.163.379,01 · ejecución 528.694,16 · saldo 2.634.684,85 · 16,71 %. Abrir el Excel en
   la hoja `Rubro` y comparar el «Total general».
4. **Filtros:** elegir financiador *CEL 2026* (1.271.361,95 / 241.717,17, igual que la hoja `Financiador`); añadir
   región *LP* y área *PROGRAMA* y mostrar que indicadores y gráficos cambian a la vez.
5. **Reporte 4 · Región:** desplegar LP → ALUMNI → CATALYST 18 → 5. Viajes → 5.2 Viajes Nacionales y abrir sus
   4 movimientos (Bs 814,20). Comparar con la hoja `Por region y Area`.
6. **Reporte 5 · Por mes:** comparar con la hoja `Por mes` (Junio: 74.320,88 / 55.030,05).
7. **Reporte 6 · Movimientos:** buscar «ALQUILER», ordenar por monto, cambiar de página.
8. **Exportar** un reporte filtrado a Excel y a PDF y abrir ambos archivos.
9. **Administración:** registrar una modificación presupuestaria y mostrar cómo cambian vigente y saldo; mostrar la
   auditoría (inicio de sesión, importación, exportaciones) y crear un usuario de consulta.
10. **Alertas y proyección:** umbrales configurables, posibles anomalías y cierre estimado, presentados como
    estimaciones.
11. Cerrar ejecutando `python -m pytest`: 31 pruebas que comparan el sistema con el Excel.
