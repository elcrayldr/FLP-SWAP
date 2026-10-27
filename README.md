# FLP-SWAP

Herramienta Windows para inspeccionar y migrar proyectos FL Studio (.flp) entre versiones.

## Motor de migración implementado

El conversor ahora procesa el flujo de eventos del FLP y aplica reglas explícitas en vez de limitarse a cambiar el número de versión:

- Reconoce la excepción de FL Studio 25.2+: el evento `0xAC` tiene un payload de 3 bytes, no de 4.
- Al convertir proyectos FL 25.2+ a destinos anteriores a 25.2, elimina el marcador `0xAC` y el banner de versión UTF-16LE `0xC0` que esos destinos no reconocen.
- **No** recorta registros de clips de playlist `0xE9` para simular una conversión. Si el destino requiere un formato de playlist más antiguo y no existe una migración campo por campo validada, detiene la conversión para evitar generar un proyecto corrupto.
- Actualiza el evento `FLVersion` y el número de build cuando el destino especifica un build.
- Si el destino no especifica build, elimina el build de origen para no dejar metadatos contradictorios.
- Valida el contenedor resultante y conserva intacto el archivo original.

Estas reglas se basan en documentación pública de análisis del formato FLP y en diferencias observadas entre guardados de FL Studio. Referencias técnicas: [flpdiff FLP format spec](https://github.com/dawhubapp/flpdiff/blob/main/docs/fl-format/flp-format-spec.md), [FL25 event findings](https://github.com/dawhubapp/flpdiff/blob/main/docs/fl-format/fl25-event-format.md), [PyFLP event model](https://pyflp.readthedocs.io/en/stable/architecture/flp-format.html).

## Límite de compatibilidad

El motor tiene reglas limitadas para algunas diferencias estructurales, pero todavía no es un conversor universal. No puede reconstruir genéricamente el estado privado de cualquier plugin ni adivinar la semántica de todos los eventos desconocidos. En particular, una conversión entre versiones mayores puede conservar parámetros que la versión de destino no entiende. Por eso el informe distingue entre **archivo convertido** y **compatibilidad verificada**. La prueba final requiere abrir y reproducir el proyecto en la versión destino.

## Uso

1. Selecciona un archivo `.flp`.
2. Selecciona la versión destino.
3. Pulsa **Convertir copia** y guarda el resultado con otro nombre.
4. Abre la copia en la versión destino y revisa playlist, notas, automatizaciones, mezclador, plugins, muestras y reproducción.

No sobrescribe el archivo original.

## Versiones seleccionables

El catálogo de interfaz incluye las 110 etiquetas de versiones solicitadas, desde FruityLoops 1.0.0 hasta FL Studio 2026.1.7. La lista de etiquetas no significa que existan reglas de migración específicas y verificadas para cada pareja posible de versiones.

## Construcción en Windows

Requiere Python 3.11+:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m flpswap
```

Para compilar:

```bat
build_windows.bat
```

GitHub Actions genera los artefactos de Windows en [Actions](https://github.com/elcrayldr/FLP-SWAP/actions).

## Próximas reglas

El siguiente trabajo es crear fixtures de proyectos reales guardados por cada versión y probar apertura/reproducción en FL Studio. Las reglas se añadirán solo tras verificar diferencias entre archivos; no se deben eliminar ni recortar datos desconocidos solo por su número de evento.
