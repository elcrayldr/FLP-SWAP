"""Tkinter interface for FLP SWAP's read-only inspection foundation."""
from pathlib import Path
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from flpswap import __version__
from flpswap.flp_inspector import inspect_flp
from flpswap.compatibility import assess_compatibility
from flpswap.flp_parser import FlpFormatError, parse_flp_metadata
from flpswap.version_detector import detect_installations


TARGET_VERSIONS = (
    "FL Studio 11.0.0", "FL Studio 11.1.0", "FL Studio 11.1.3",
    "FL Studio 12.0.0", "FL Studio 12.1.0", "FL Studio 12.2.0",
    "FL Studio 12.3.0", "FL Studio 12.4.0", "FL Studio 12.5.0",
    "FL Studio 12.5.1", "FL Studio 20.0.0", "FL Studio 20.1.0",
    "FL Studio 20.5.0", "FL Studio 20.6.0", "FL Studio 20.7.0",
    "FL Studio 20.8.0", "FL Studio 20.9.0", "FL Studio 20.9.2",
    "FL Studio 21.0.0", "FL Studio 21.1.0", "FL Studio 21.2.0",
    "FL Studio 21.2.3", "FL Studio 24.1.0", "FL Studio 24.1.2",
    "FL Studio 2025.1.0", "FL Studio 2025.2.5", "FL Studio 26.1.1",
    "FL Studio 26.1.4", "FL Studio 26.1.7",
)


class FLPSwapApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"FLP SWAP {__version__}")
        self.geometry("880x620")
        self.minsize(720, 500)
        self.configure(bg="#15171b")
        self.selected_file: Path | None = None
        self._style()
        self._build()

    def _style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#15171b")
        style.configure("TLabel", background="#15171b", foreground="#f2f2f2")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("TButton", padding=8)
        style.configure("Treeview", rowheight=26)

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="FLP SWAP", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="1. Selecciona un proyecto FLP.  2. Elige la versión de destino.",
        ).pack(anchor="w", pady=(4, 16))

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="1. Seleccionar proyecto FLP", command=self.choose_file).pack(side="left")
        ttk.Label(actions, text="2. Versión destino:").pack(side="left", padx=(12, 5))
        self.target_version = tk.StringVar(value="FL Studio 26.1.7")
        self.target_combo = ttk.Combobox(
            actions, textvariable=self.target_version, values=TARGET_VERSIONS,
            state="readonly", width=22,
        )
        self.target_combo.pack(side="left")
        self.target_combo.bind("<<ComboboxSelected>>", self.on_target_changed)
        ttk.Button(actions, text="Exportar informe", command=self.export_report).pack(side="left", padx=8)
        ttk.Button(actions, text="Detectar FL instalado", command=self.show_installations).pack(side="left")

        self.file_label = ttk.Label(outer, text="Ningún proyecto seleccionado")
        self.file_label.pack(anchor="w", pady=8)

        self.output = tk.Text(
            outer, wrap="word", bg="#202329", fg="#e8e8e8",
            insertbackground="#ffffff", relief="flat", padx=12, pady=12,
            font=("Consolas", 10),
        )
        self.output.pack(fill="both", expand=True)
        self.output.insert("1.0", (
            "PASO 1 — Selecciona tu archivo .flp. La aplicación leerá la versión guardada dentro del proyecto, si está disponible.\n\n"
            "PASO 2 — Selecciona la versión de destino en la lista desplegable (por defecto, FL Studio 26.1.7).\n\n"
            "IMPORTANTE: esta compilación inspecciona el proyecto y compara versiones. Todavía no modifica ni convierte archivos.\n"
        ))
        self.output.configure(state="disabled")
        self.last_report: dict = {"application_version": __version__, "status": "idle"}

    def _write(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def choose_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Seleccionar proyecto FL Studio",
            filetypes=[("Proyectos FL Studio", "*.flp"), ("Todos los archivos", "*.*")],
        )
        if not selected:
            return
        self.selected_file = Path(selected)
        try:
            inspected = inspect_flp(self.selected_file)
            metadata = parse_flp_metadata(self.selected_file)
            metadata_report = {
                "valid_container": metadata.valid_container,
                "header_length": metadata.header_length,
                "format_id": metadata.format_id,
                "channel_count": metadata.channel_count,
                "ppq": metadata.ppq,
                "event_bytes": metadata.event_bytes,
                "event_count": metadata.event_count,
                "saved_version": metadata.saved_version,
                "warnings": list(metadata.warnings),
            }
        except (OSError, ValueError, FlpFormatError) as exc:
            messagebox.showerror("No se pudo inspeccionar", str(exc))
            return

        self.file_label.configure(text=str(self.selected_file))
        try:
            target_numeric = self.target_version.get().replace("FL Studio ", "").strip()
            assessment = assess_compatibility(metadata.saved_version, target_numeric)
            assessment_report = assessment.to_dict()
        except ValueError as exc:
            messagebox.showerror("Versión destino no válida", str(exc))
            return

        self.last_report = {
            "application_version": __version__,
            "selected_target_version": target_numeric,
            "inspection": {
                "path": inspected.path,
                "size_bytes": inspected.size_bytes,
                "sha256": inspected.sha256,
                "signature_hex": inspected.signature_hex,
                "signature_ascii": inspected.signature_ascii,
                "status": inspected.status,
                "notes": list(inspected.notes),
            },
            "flp_metadata": metadata_report,
            "compatibility_assessment": assessment_report,
            "conversion": {
                "performed": False,
                "status": "not_implemented",
                "message": "La detección de versión no implica compatibilidad ni conversión.",
            },
        }
        source_display = metadata.saved_version or "No identificada"
        relation_text = {
            "same_version": "El proyecto y la versión de destino coinciden.",
            "source_older_than_target": "El proyecto parece proceder de una versión anterior a la seleccionada.",
            "source_newer_than_target": "ATENCIÓN: el proyecto parece proceder de una versión posterior a la seleccionada.",
            "unknown": "No se ha podido determinar con seguridad la versión de origen.",
        }.get(assessment_report["relation"], assessment_report["relation"])
        self._write(
            f"PROYECTO: {self.selected_file.name}\n"
            f"VERSIÓN DETECTADA EN EL FLP: {source_display}\n"
            f"VERSIÓN DE DESTINO SELECCIONADA: {target_numeric}\n\n"
            f"RESULTADO: {relation_text}\n\n"
            f"Tamaño: {inspected.size_bytes:,} bytes\n"
            f"Eventos FLP analizados: {metadata.event_count}\n"
            f"Contenedor FLP válido: {'Sí' if metadata.valid_container else 'No'}\n\n"
            "ESTADO DE CONVERSIÓN: NO REALIZADA.\n"
            "Esta versión de prueba no modifica el proyecto.\n\n"
            "AVISOS:\n- " + "\n- ".join(assessment_report["warnings"])
        )

    def on_target_changed(self, _event=None) -> None:
        if self.selected_file is None:
            return
        try:
            metadata = parse_flp_metadata(self.selected_file)
            target_numeric = self.target_version.get().replace("FL Studio ", "").strip()
            assessment = assess_compatibility(metadata.saved_version, target_numeric)
            self.last_report["selected_target_version"] = target_numeric
            self.last_report["compatibility_assessment"] = assessment.to_dict()
            source_display = metadata.saved_version or "No identificada"
            relation_text = {
                "same_version": "El proyecto y la versión de destino coinciden.",
                "source_older_than_target": "El proyecto parece proceder de una versión anterior a la seleccionada.",
                "source_newer_than_target": "ATENCIÓN: el proyecto parece proceder de una versión posterior a la seleccionada.",
                "unknown": "No se ha podido determinar con seguridad la versión de origen.",
            }.get(assessment.relation, assessment.relation)
            self._write(
                f"PROYECTO: {self.selected_file.name}\n"
                f"VERSIÓN DETECTADA EN EL FLP: {source_display}\n"
                f"VERSIÓN DE DESTINO SELECCIONADA: {target_numeric}\n\n"
                f"RESULTADO: {relation_text}\n\n"
                "ESTADO DE CONVERSIÓN: NO REALIZADA.\n"
                "Esta versión de prueba no modifica el proyecto."
            )
        except (OSError, ValueError, FlpFormatError) as exc:
            messagebox.showerror("No se pudo actualizar el análisis", str(exc))

    def show_installations(self) -> None:
        installs = detect_installations()
        self.last_report["installations"] = [
            {"executable": item.executable, "file_version": item.file_version, "source": item.source}
            for item in installs
        ]
        if installs:
            lines = ["Instalaciones detectadas:"]
            for item in installs:
                lines.append(f"- {item.executable}\n  Versión de archivo: {item.file_version or 'desconocida'}")
        else:
            lines = [
                "No se han encontrado instalaciones en las rutas conocidas.",
                "Esto no demuestra que FL Studio no esté instalado; la detección se ampliará.",
                f"Sistema actual: {__import__('platform').platform()}",
            ]
        self._write("\n".join(lines))

    def export_report(self) -> None:
        if not self.last_report or self.last_report.get("status") == "idle":
            messagebox.showinfo("Sin informe", "Selecciona primero un proyecto FLP.")
            return
        target = filedialog.asksaveasfilename(
            title="Guardar informe", defaultextension=".json",
            filetypes=[("Informe JSON", "*.json"), ("Texto", "*.txt")],
        )
        if not target:
            return
        try:
            Path(target).write_text(
                json.dumps(self.last_report, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            messagebox.showerror("Error al guardar", str(exc))
            return
        messagebox.showinfo("Informe guardado", f"Informe guardado en:\n{target}")


def main() -> None:
    FLPSwapApp().mainloop()
