# SVG Pipeline Unificado

Este paquete separa las dos capas para que no se pisen entre sí:

- **Capa de origen**: ancla y normaliza el SVG.
- **Capa de optimización**: reordena rutas y reduce recorrido.
- **Cadena completa**: origen → optimización.

## Archivos

- `svg_unificado_app.py`: interfaz unificada.
- `svg_origen.py`: capa de origen.
- `svg_optimizer.py`: capa de optimización.
- `run_streamlit.bat`: abre la interfaz.
- `build_exe.bat`: construye un `.exe` con PyInstaller.

## Instalación local

```bash
python -m pip install -r requirements.txt
```

## Ejecutar

```bash
streamlit run svg_unificado_app.py
```

O con el acceso directo por lote:

```bash
run_streamlit.bat
```

## Crear ejecutable

```bash
build_exe.bat
```

El ejecutable queda en `dist\SVG_Pipeline_Unificado.exe`.

## Crear acceso directo

1. Crea el `.exe` con `build_exe.bat`.
2. Clic derecho sobre `dist\SVG_Pipeline_Unificado.exe`.
3. Enviar a → Escritorio (crear acceso directo).

## Commit en tu repositorio

No puedo hacer el commit desde aquí porque no tengo acceso a tu repo local, pero los archivos ya quedan listos para:
```bash
git add .
git commit -m "Unify SVG origin and optimization pipeline"
git push
```

## Orden recomendado

La secuencia más segura es:

1. **Origen**
2. **Optimización**

Así la capa de optimización trabaja sobre coordenadas ya normalizadas y no sobre un árbol que todavía puede moverse.