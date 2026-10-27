"""Tkinter interface for FLP SWAP's current inspection foundation."""
from pathlib import Path
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from flpswap import __version__
from flpswap.flp_inspector import inspect_flp
from flpswap.version_detector import detect_installations


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
            text="Inspección segura de proyectos · La conversión se habilitará por reglas verificadas",
        ).pack(anchor="w", pady=(4, 16))

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Seleccionar proyecto FLP", command=self.choose_file).pack(side="left")
        ttk.Button(actions, text="Detectar FL Studio instalado", command=self.show_installations).pack(side="left", padx=8)
        ttk.Button(actions, text="Exportar informe", command=self.export_report).pack(side="left")

        self.file_label = ttk.Label(outer, text="Ningún proyecto seleccionado")
        self.file_label.pack(anchor="w", pady=8)

        self.output = tk.Text(
            outer, wrap="word", bg="#202329", fg="#e8e8e8",
            insertbackground="#ffffff", relief="flat", padx=12, pady=12,
            font=("Consolas", 10),
        )
        self.output.pack(fill="both", expand=True)
        self.output.insert("1.0", (
            "Estado: inspección conservadora\n\n"
            "Esta versión no modifica ni convierte proyectos. Selecciona un FLP para obtener "
            "tamaño, SHA-256 y una inspección preliminar. No se inferirá una versión exacta "
            "a partir de datos no verificados.\n"
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
            result = inspect_flp(self.selected_file)
        except (OSError, ValueError) as exc:
            messagebox.showerror("No se pudo inspeccionar", str(exc))
            return
        self.file_label.configure(text=str(self.selected_file))
        self.last_report = {
            "application_version": __version__,
            "inspection": {
                "path": result.path,
                "size_bytes": result.size_bytes,
                "sha256": result.sha256,
                "signature_hex": result.signature_hex,
                "signature_ascii": result.signature_ascii,
                "status": result.status,
                "notes": list(result.notes),
            },
            "conversion": {"performed": False, "status": "not_implemented"},
        }
        self._write(json.dumps(self.last_report, indent=2, ensure_ascii=False))

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
