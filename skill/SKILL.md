---
name: nps-upcoming-selam
description: Corre el Upcoming de NPS de BTS SELAM (Argentina, Brasil con Nexo, México) directo desde Salesforce y en solo lectura - qué encuestas NPS y de facilitadores faltan crear, cuáles ya existen (con QR y links), excluidos y revisión manual con motivo, casos especiales y la página para copiar las tarjetas al canvas de Slack. Usar cuando pidan los NPS de la semana, de un día o de un rango, buscar sesiones por cliente, proyecto, facilitador o país, o preparar lo de #latam-nps.
---

# NPS Upcoming SELAM (V2-1, solo lectura)

Este skill reemplaza la corrida de los lunes de la app de escritorio. Un motor
determinístico (`nps_v2`, con las reglas certificadas de `engine/stages`) decide
todo; vos solo orquestás: ejecutás los comandos, corrés en Salesforce **exactamente**
las consultas que el motor imprime y mostrás los resultados.

## Reglas que no se negocian

1. **Solo lectura.** No crees, modifiques ni borres nada en Salesforce, Slack, Outlook
   ni Box. No publiques en Slack. (Crear encuestas y publicar llegan en V2-2 y V2-3.)
2. **Las consultas las escribe el motor.** Copiá cada `soql` tal cual en
   `salesforce_query` (conector BTS). No la reformatees, no la "mejores", no escribas
   consultas propias para completar datos.
3. **El motor decide.** No apliques criterio propio sobre elegibilidad, exclusiones,
   encuestas o idioma. Si algo te parece raro, decilo como observación, sin cambiar
   el resultado.
4. **Ante `"status": "error"`, frená.** Mostrá el mensaje tal cual, explicalo en
   palabras simples y no busques atajos. Única excepción: si es
   `ControlMismatchError`, los datos pudieron cambiar entre consultas; repetí la
   corrida completa **una vez** en una carpeta nueva. Si vuelve a fallar, frená.
5. **Los datos reales quedan en la sesión.** La carpeta de la corrida va en el
   espacio de trabajo de la sesión, nunca en un repositorio ni en otro lugar.

## Cómo se corre

Definí, una sola vez por corrida:

- `SKILL_DIR`: la carpeta que contiene este `SKILL.md`.
- `RUN_DIR`: `<espacio de trabajo>/nps-runs/<run-id>`, con un `run-id` nuevo y
  descriptivo, por ejemplo `V2-20261130-0915-semana-30-11`. Nunca reutilices una
  carpeta.
- El comando base (Linux/macOS):

  ```bash
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$SKILL_DIR" python3 -m nps_v2 <comando> ...
  ```

Cada comando imprime JSON. Leé siempre `status` antes de seguir.

### 1. Selección

Traducí el pedido a argumentos de `select`. Si falta la fecha, usá **hoy en Buenos
Aires** para la semana estándar. Si el pedido es ambiguo, hacé una sola pregunta.

| Pedido | Argumentos |
|---|---|
| "la semana", "los NPS del lunes" | `--week-of <fecha>` (cualquier día de esa semana; ventana martes→lunes siguiente) |
| "sumá/restá días" | además `--extend-start N` / `--extend-end N` (negativo achica) |
| "solo mañana", "el jueves 3" | `--day <AAAA-MM-DD>` |
| "del 1 al 5" | `--from <AAAA-MM-DD> --to <AAAA-MM-DD>` |
| "solo Brasil" | `--country BR` (repetible: AR, BR, MX; Brasil incluye Nexo) |
| "del cliente X", "las de tal facilitador" | `--client`, `--project`, `--facilitator`, `--sub-type` (contiene, sin tildes ni mayúsculas) |

```bash
... python3 -m nps_v2 select --run "$RUN_DIR" --week-of 2026-11-30
```

### 2. Proyectos

Por cada elemento de `queries` del paso anterior (son dos: `projects` y
`projects_control`): ejecutá `salesforce_query` con su `soql` exacto. Después:

```bash
... python3 -m nps_v2 capture --run "$RUN_DIR" --group projects
```

`capture` copia las respuestas desde el registro de la sesión, así no tenés que
re-escribir datos. Si informa algo en `missing`, guardá **a mano** la respuesta
completa de esa consulta, sin tocar nada, en la ruta `save_as` indicada, y repetí
`capture` hasta que `missing` quede vacío.

### 3. Encuestas existentes

```bash
... python3 -m nps_v2 surveys --run "$RUN_DIR"
```

Verifica los proyectos contra el control. Ejecutá cada consulta de `queries` (pares
`survey_sets_NN` y `survey_sets_NN_control`; pueden ser cero) y después
`capture --group survey_sets`, igual que en el paso 2.

### 4. Resultado

```bash
... python3 -m nps_v2 upcoming --run "$RUN_DIR"
```

Si devuelve `"status": "ok"`, en `outputs` están:

- `preview.md`: vista previa en español (pendientes, ya creadas, revisión, excluidos
  con motivo, fuera de alcance, casos especiales, calidad de datos).
- `slack_html`: la página para Slack (tarjetas por sesión con QR, botón
  "Copiar para Slack" por cliente).

### 5. Qué mostrarle al usuario

1. Una tabla corta con el `summary`: encuestas a crear (sesiones y encuestas),
   ya creadas, revisión manual, excluidos, fuera de alcance, casos especiales y notas
   de calidad.
2. Las sesiones con encuestas a crear (país, fecha, cliente, sesión, qué falta).
3. Los casos especiales: avisá que requieren mail personalizado.
4. Si `watchlist_configured` es `false`, avisá que la lista de facilitadores
   especiales no está instalada y que no se marcaron casos especiales.
5. Entregá `preview.md` y la página de Slack con la herramienta para enviar archivos
   (que se puedan ver en el panel). Recordá que, si el visor no deja copiar, la
   página abre la tabla seleccionada para Ctrl+C, y que en Chrome o Edge copia
   directo.

## Problemas frecuentes

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| `ControlMismatchError` | Lo guardado no coincide con los conteos de Salesforce | Repetir la corrida completa una vez en carpeta nueva |
| `ReaderError ... done is not true` o `may be truncated` | Respuesta incompleta o demasiado grande | Achicar la selección (menos días o un país) |
| `RunFolderError ... Missing response` | Falta guardar una respuesta | Ejecutar esa consulta y `capture` (o guardarla a mano) |
| `run 'surveys' again` | Las consultas de encuestas no corresponden a los proyectos guardados | Repetir el paso 3 |
| `RegistryError` / `WatchlistError` | Configuración del skill inválida | Frenar y avisar: hay que reinstalar el skill |

## Qué hay en este skill

`nps_v2/` (motor V2), `engine/` (solo las etapas certificadas que usa: normalize,
business_rules, worklist y los ayudantes del renderer), `config/` (reglas de negocio,
registro de países, alcance del reporte; `config/v2/watchlist.json` solo si se
instaló la lista de casos especiales) y `BUILD_INFO.json` (versión, commit y huellas
de cada archivo). Se genera con `python -m scripts.build_skill` desde el repositorio.
