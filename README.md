# FLP-SWAP

Aplicación Windows para inspeccionar proyectos FL Studio (.flp) y generar una copia cambiando sus metadatos de versión.

## Qué hace ahora el motor

- Lee y valida la cabecera y el bloque de eventos del FLP.
- Localiza el evento `FLVersion` y lo cambia por la versión de destino seleccionada.
- Si la versión de destino incluye un número de build y el proyecto tiene el evento `FLBuild`, actualiza ese campo también.
- Preserva byte a byte todos los demás eventos, incluidos datos opacos y estados de plugins que el programa no entiende.
- Valida el resultado y nunca sobrescribe el archivo original.

Esto es más seguro que parsear y volver a serializar todo el proyecto con una biblioteca de terceros que podría descartar eventos desconocidos.

## Límite importante

**Cambiar los metadatos de versión no equivale a traducir todas las funciones del proyecto.** Si el FLP usa instrumentos, efectos, automatizaciones, formatos de plugin o eventos que la versión de destino no admite, estos datos se conservan, pero la versión antigua todavía podría ignorarlos o rechazar el proyecto. El programa no convierte automáticamente plugins VST/VST3 ni recrea parámetros incompatibles.

Por tanto, FLP-SWAP ya ejecuta una modificación real y conservadora del archivo, pero todavía no es un conversor semántico universal de FL Studio 1–26. No debe anunciarse como compatible hasta probar el resultado en la versión destino.

## Flujo de uso

1. Selecciona un archivo `.flp`.
2. Selecciona la versión de destino.
3. Pulsa **Convertir copia** y elige un nombre nuevo.
4. Abre la copia en la versión destino y comprueba patrones, notas, playlist, automatizaciones, mezclador, plugins, muestras y reproducción.

Conserva siempre el archivo original.

## Versiones seleccionables

El catálogo de interfaz incluye las 110 etiquetas de versiones aportadas para este proyecto, desde FruityLoops 1.0.0 hasta FL Studio 2026.1.7. La disponibilidad de una etiqueta en la lista no implica que todas las características de esa versión se puedan migrar.

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

La aplicación portable queda en `dist\FLPSwap\FLPSwap.exe`. GitHub Actions genera los artefactos de Windows en la pestaña [Actions](https://github.com/elcrayldr/FLP-SWAP/actions).

## Dependencias y licencia

El repositorio conserva PyFLP como dependencia de diagnóstico/desarrollo, aunque el motor de modificación de versión actual trabaja directamente con los bytes del FLP. PyFLP es un proyecto independiente, no oficial y distribuido bajo GPL-3.0-or-later: https://github.com/demberto/PyFLP.

## Próxima fase necesaria para conversión funcional

La siguiente fase es un sistema de reglas por versiones: identificar eventos y características añadidos/cambiados entre releases, aplicar migraciones verificables para reglas conocidas y emitir un informe de las funciones que no se pueden traducir. La compatibilidad real debe probarse abriendo los archivos con las versiones de FL Studio correspondientes; cambiar el campo de versión no sustituye esa prueba.
