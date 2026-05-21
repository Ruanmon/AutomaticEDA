#!/usr/bin/env python3
"""Modern GUI client for the AutomaticEDA Error Log Analyzer.

Launch with::

    python gui.py
"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font, messagebox, scrolledtext, ttk

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Color & style constants (light modern palette)
# ---------------------------------------------------------------------------
BG = "#F0F2F5"          # window / panel background
SURFACE = "#FFFFFF"      # card surface
PRIMARY = "#2563EB"      # main accent (blue)
PRIMARY_DARK = "#1D4ED8" # hover accent
PRIMARY_LIGHT = "#DBEAFE" # light tint
SECONDARY = "#64748B"    # secondary text
BORDER = "#E2E8F0"       # divider / border
SUCCESS = "#10B981"      # green status
ERROR_CLR = "#EF4444"    # red status
TEXT = "#1E293B"         # primary text
TEXT_MUTED = "#94A3B8"   # placeholder text
RADIUS = 8               # corner radius (used for canvas-drawn widgets)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _make_placeholder(widget: tk.Text, placeholder: str) -> None:
    """Attach placeholder-text behaviour to a tk.Text widget."""
    widget._placeholder = placeholder
    widget._has_placeholder = False

    def _show():
        if not widget.get("1.0", "end-1c"):
            widget._has_placeholder = True
            widget.insert("1.0", placeholder)
            widget.config(fg=TEXT_MUTED)

    def _hide(event=None):  # noqa: ARG001
        if widget._has_placeholder:
            widget.delete("1.0", tk.END)
            widget._has_placeholder = False
            widget.config(fg=TEXT)

    widget.bind("<FocusIn>", _hide)
    widget.bind("<FocusOut>", lambda e: _show())
    _show()


def _get_text(widget: tk.Text) -> str:
    """Return stripped text, ignoring placeholder content."""
    if getattr(widget, "_has_placeholder", False):
        return ""
    return widget.get("1.0", "end-1c").strip()


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("AutomaticEDA — Error Log Analyzer")
        self.geometry("1080x760")
        self.minsize(860, 620)
        self.configure(bg=BG)

        # Intercept close so we can warn about running analysis
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._setup_fonts()
        self._setup_styles()
        self._build_ui()

        # State
        self._analyzing = False

    # ------------------------------------------------------------------
    # Fonts & ttk styles
    # ------------------------------------------------------------------

    def _setup_fonts(self) -> None:
        families = font.families()
        for candidate in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Arial"):
            if candidate in families:
                base_family = candidate
                break
        else:
            base_family = "TkDefaultFont"

        self.font_h1     = font.Font(family=base_family, size=16, weight="bold")
        self.font_h2     = font.Font(family=base_family, size=11, weight="bold")
        self.font_body   = font.Font(family=base_family, size=10)
        self.font_small  = font.Font(family=base_family, size=9)
        self.font_code   = font.Font(family="Courier New", size=10)
        self.font_btn    = font.Font(family=base_family, size=11, weight="bold")

    def _setup_styles(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")

        # Generic frame / label backgrounds
        s.configure("TFrame",       background=BG)
        s.configure("Card.TFrame",  background=SURFACE, relief="flat")
        s.configure("TLabel",       background=BG,      foreground=TEXT,
                    font=self.font_body)
        s.configure("Card.TLabel",  background=SURFACE, foreground=TEXT,
                    font=self.font_body)
        s.configure("Muted.TLabel", background=SURFACE, foreground=SECONDARY,
                    font=self.font_small)
        s.configure("H1.TLabel",    background=BG,      foreground=TEXT,
                    font=self.font_h1)
        s.configure("H2.TLabel",    background=SURFACE, foreground=TEXT,
                    font=self.font_h2)

        # Entry
        s.configure("TEntry",       fieldbackground=SURFACE, foreground=TEXT,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                    insertcolor=TEXT, relief="flat", padding=6)
        s.map("TEntry",
              bordercolor=[("focus", PRIMARY), ("!focus", BORDER)])

        # Combobox
        s.configure("TCombobox",    fieldbackground=SURFACE, foreground=TEXT,
                    selectbackground=PRIMARY_LIGHT, selectforeground=TEXT,
                    bordercolor=BORDER, arrowcolor=SECONDARY, relief="flat",
                    padding=6)
        s.map("TCombobox",
              bordercolor=[("focus", PRIMARY)])

        # Scrollbar
        s.configure("Vertical.TScrollbar",
                    background=BORDER, troughcolor=SURFACE,
                    bordercolor=SURFACE, arrowcolor=SECONDARY, relief="flat")

        # Separator
        s.configure("TSeparator", background=BORDER)

        # Progressbar (used as spinner stripe)
        s.configure("Accent.Horizontal.TProgressbar",
                    troughcolor=PRIMARY_LIGHT, background=PRIMARY,
                    bordercolor=PRIMARY_LIGHT, relief="flat", thickness=4)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ── Top bar ──────────────────────────────────────────────────
        self._build_topbar()

        # ── Config strip ─────────────────────────────────────────────
        self._build_config_strip()

        # ── Body  (left column + right column) ───────────────────────
        body = ttk.Frame(self, style="TFrame")
        body.pack(fill="both", expand=True, padx=18, pady=(0, 6))
        body.columnconfigure(0, weight=2, minsize=240)
        body.columnconfigure(1, weight=5)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_right_panel(body)

        # ── Action bar ───────────────────────────────────────────────
        self._build_action_bar()

        # ── Results panel ────────────────────────────────────────────
        self._build_results_panel()

    # ── Top bar ──────────────────────────────────────────────────────

    def _build_topbar(self) -> None:
        bar = tk.Frame(self, bg=PRIMARY, height=56)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        icon_lbl = tk.Label(bar, text="⚡", bg=PRIMARY, fg="#FFFFFF",
                            font=font.Font(size=22))
        icon_lbl.pack(side="left", padx=(18, 4), pady=8)

        title_lbl = tk.Label(bar, text="AutomaticEDA", bg=PRIMARY, fg="#FFFFFF",
                             font=self.font_h1)
        title_lbl.pack(side="left", pady=8)

        sub_lbl = tk.Label(bar, text="  —  Error Log Analyzer",
                           bg=PRIMARY, fg="#BFDBFE", font=self.font_body)
        sub_lbl.pack(side="left", pady=8)

    # ── Config strip ─────────────────────────────────────────────────

    def _build_config_strip(self) -> None:
        strip = tk.Frame(self, bg=SURFACE, bd=0, relief="flat")
        strip.pack(fill="x", padx=0, pady=0)

        inner = tk.Frame(strip, bg=SURFACE)
        inner.pack(fill="x", padx=18, pady=10)

        # API key
        tk.Label(inner, text="OpenAI API Key", bg=SURFACE, fg=SECONDARY,
                 font=self.font_small).grid(row=0, column=0, sticky="w", padx=(0, 6))

        self._api_key_var = tk.StringVar(value=os.environ.get("OPENAI_API_KEY", ""))
        api_entry = ttk.Entry(inner, textvariable=self._api_key_var, show="●",
                              width=34)
        api_entry.grid(row=0, column=1, sticky="ew", padx=(0, 18))

        # Model
        tk.Label(inner, text="Model", bg=SURFACE, fg=SECONDARY,
                 font=self.font_small).grid(row=0, column=2, sticky="w", padx=(0, 6))

        self._model_var = tk.StringVar(value="gpt-4o")
        model_cb = ttk.Combobox(inner, textvariable=self._model_var, width=16,
                                values=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
                                        "gpt-3.5-turbo"],
                                state="readonly")
        model_cb.grid(row=0, column=3, sticky="ew", padx=(0, 18))

        # Status badge
        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(inner, textvariable=self._status_var,
                                    bg=SURFACE, fg=SECONDARY, font=self.font_small)
        self._status_lbl.grid(row=0, column=4, sticky="w")

        inner.columnconfigure(1, weight=1)

        # Divider
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

    # ── Left panel — RTL directory ────────────────────────────────────

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        card = tk.Frame(parent, bg=SURFACE, bd=0, relief="flat")
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)

        # Section header
        tk.Label(card, text="RTL 工程目录", bg=SURFACE, fg=TEXT,
                 font=self.font_h2).pack(anchor="w", padx=14, pady=(12, 4))
        tk.Label(card, text="选择包含 .sv / .v 文件的目录",
                 bg=SURFACE, fg=SECONDARY, font=self.font_small
                 ).pack(anchor="w", padx=14, pady=(0, 8))

        # Path row
        path_row = tk.Frame(card, bg=SURFACE)
        path_row.pack(fill="x", padx=14, pady=(0, 8))

        self._rtl_dir_var = tk.StringVar(value="")
        path_entry = ttk.Entry(path_row, textvariable=self._rtl_dir_var)
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        path_entry.bind("<Return>", lambda e: self._load_rtl_dir())

        browse_btn = self._flat_button(path_row, "📁 浏览", self._browse_rtl_dir,
                                       bg=PRIMARY, fg="#FFFFFF", padx=10)
        browse_btn.pack(side="left")

        # Divider
        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", padx=14, pady=4)

        # File list header
        self._file_count_var = tk.StringVar(value="未选择目录")
        tk.Label(card, textvariable=self._file_count_var,
                 bg=SURFACE, fg=SECONDARY, font=self.font_small,
                 anchor="w").pack(fill="x", padx=14, pady=(4, 2))

        # Scrollable file list
        list_frame = tk.Frame(card, bg=SURFACE)
        list_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        vsb = ttk.Scrollbar(list_frame, orient="vertical")
        self._file_listbox = tk.Listbox(
            list_frame, yscrollcommand=vsb.set,
            bg=SURFACE, fg=TEXT, selectbackground=PRIMARY_LIGHT,
            selectforeground=TEXT, activestyle="none",
            font=self.font_code, relief="flat", bd=0,
            highlightthickness=0, borderwidth=0,
        )
        vsb.config(command=self._file_listbox.yview)
        self._file_listbox.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._rtl_files: dict[str, str] = {}

    # ── Right panel — error log input ────────────────────────────────

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        card = tk.Frame(parent, bg=SURFACE, bd=0, relief="flat")
        card.grid(row=0, column=1, sticky="nsew", pady=8)

        # Header row
        hdr = tk.Frame(card, bg=SURFACE)
        hdr.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(hdr, text="仿真 Error Log", bg=SURFACE, fg=TEXT,
                 font=self.font_h2).pack(side="left")

        clear_btn = self._flat_button(hdr, "✕ 清空", self._clear_log,
                                      bg=BORDER, fg=SECONDARY, padx=8)
        clear_btn.pack(side="right")

        paste_btn = self._flat_button(hdr, "📋 粘贴", self._paste_log,
                                      bg=PRIMARY_LIGHT, fg=PRIMARY, padx=8)
        paste_btn.pack(side="right", padx=(0, 6))

        tk.Label(card, text="粘贴来自 VCS / ModelSim / Xcelium 等工具的错误输出",
                 bg=SURFACE, fg=SECONDARY, font=self.font_small,
                 anchor="w").pack(fill="x", padx=14, pady=(0, 8))

        # Text area
        text_frame = tk.Frame(card, bg=BORDER, bd=1, relief="flat")
        text_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        vsb2 = ttk.Scrollbar(text_frame, orient="vertical")
        self._log_text = tk.Text(
            text_frame, yscrollcommand=vsb2.set,
            font=self.font_code, bg=SURFACE, fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=0,
            wrap="word", highlightthickness=0, padx=10, pady=8,
        )
        vsb2.config(command=self._log_text.yview)
        self._log_text.pack(side="left", fill="both", expand=True)
        vsb2.pack(side="right", fill="y")

        _make_placeholder(
            self._log_text,
            "在此粘贴仿真工具输出的 error log…\n\n"
            "示例:\n"
            "  ERROR: [VRFC 10-1412] identifier 'cnt' is not declared\n"
            "  ERROR: [XSIM 43-3318] Static elaboration of top level Verilog design failed.",
        )

    # ── Action bar ───────────────────────────────────────────────────

    def _build_action_bar(self) -> None:
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=18, pady=(0, 8))

        # Analyze button (prominent)
        self._analyze_btn = self._flat_button(
            bar, "🔍  开始分析", self._start_analysis,
            bg=PRIMARY, fg="#FFFFFF", padx=32, pady=10,
            label_font=self.font_btn,
        )
        self._analyze_btn.pack(side="right")

        # Progress bar (hidden until analyzing)
        self._progress = ttk.Progressbar(
            bar, mode="indeterminate", length=200,
            style="Accent.Horizontal.TProgressbar",
        )

    # ── Results panel ────────────────────────────────────────────────

    def _build_results_panel(self) -> None:
        # Divider
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        results_outer = tk.Frame(self, bg=SURFACE)
        results_outer.pack(fill="both", expand=True)

        # Header row
        hdr = tk.Frame(results_outer, bg=SURFACE)
        hdr.pack(fill="x", padx=18, pady=(10, 4))

        tk.Label(hdr, text="分析结果", bg=SURFACE, fg=TEXT,
                 font=self.font_h2).pack(side="left")

        copy_btn = self._flat_button(hdr, "📋 复制结果", self._copy_results,
                                     bg=PRIMARY_LIGHT, fg=PRIMARY, padx=10)
        copy_btn.pack(side="right")

        save_btn = self._flat_button(hdr, "💾 保存结果", self._save_results,
                                     bg=BORDER, fg=SECONDARY, padx=10)
        save_btn.pack(side="right", padx=(0, 6))

        # Results text
        text_frame = tk.Frame(results_outer, bg=SURFACE)
        text_frame.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        vsb3 = ttk.Scrollbar(text_frame, orient="vertical")
        self._result_text = tk.Text(
            text_frame, yscrollcommand=vsb3.set,
            font=self.font_body, bg="#F8FAFC", fg=TEXT,
            relief="flat", bd=0, wrap="word",
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=PRIMARY, padx=14, pady=12,
            state="disabled",
        )
        vsb3.config(command=self._result_text.yview)
        self._result_text.pack(side="left", fill="both", expand=True)
        vsb3.pack(side="right", fill="y")

        # Configure result text tags for rich rendering
        self._result_text.tag_configure("header",
            font=font.Font(family=self.font_h2.cget("family"), size=11, weight="bold"),
            foreground=PRIMARY, spacing1=8, spacing3=4)
        self._result_text.tag_configure("body",
            font=self.font_body, foreground=TEXT, spacing1=2)
        self._result_text.tag_configure("placeholder",
            foreground=TEXT_MUTED, font=self.font_body)
        self._result_text.tag_configure("error_tag",
            foreground=ERROR_CLR, font=self.font_body)
        self._result_text.tag_configure("success_tag",
            foreground=SUCCESS, font=self.font_body)
        self._result_text.tag_configure("code",
            font=self.font_code, foreground="#1E3A5F",
            background="#EFF6FF", relief="flat")

        self._set_result_placeholder()

    # ------------------------------------------------------------------
    # Helper: flat styled button
    # ------------------------------------------------------------------

    def _flat_button(
        self, parent, text: str, command,
        bg: str = SURFACE, fg: str = TEXT,
        padx: int = 12, pady: int = 6,
        label_font=None,
    ) -> tk.Label:
        """Return a Label styled as a clickable button."""
        if label_font is None:
            label_font = self.font_body
        btn = tk.Label(parent, text=text, bg=bg, fg=fg, font=label_font,
                       padx=padx, pady=pady, cursor="hand2", relief="flat")
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e: btn.config(bg=self._darken(bg, 12)))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    @staticmethod
    def _darken(hex_color: str, amount: int = 20) -> str:
        """Darken a hex color by *amount* on each RGB channel."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return "#" + hex_color
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = max(0, r - amount), max(0, g - amount), max(0, b - amount)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _browse_rtl_dir(self) -> None:
        chosen = filedialog.askdirectory(title="选择 RTL 工程目录")
        if chosen:
            self._rtl_dir_var.set(chosen)
            self._load_rtl_dir()

    def _load_rtl_dir(self) -> None:
        dir_path = self._rtl_dir_var.get().strip()
        if not dir_path:
            return
        p = Path(dir_path)
        if not p.is_dir():
            self._file_count_var.set("⚠ 路径不存在")
            return

        # Import here so the module-level import is not required at top-level
        try:
            from eda_agent.utils.rtl_searcher import collect_rtl_files
        except ImportError:
            messagebox.showerror("错误", "找不到 eda_agent 模块，请检查安装。")
            return

        try:
            rtl_files = collect_rtl_files(p)
        except NotADirectoryError as exc:
            self._file_count_var.set(f"⚠ {exc}")
            return

        self._rtl_files = rtl_files
        self._file_listbox.delete(0, tk.END)
        for name in sorted(rtl_files):
            self._file_listbox.insert(tk.END, f"  📄 {name}")

        n = len(rtl_files)
        if n == 0:
            self._file_count_var.set("⚠ 未找到 RTL 文件")
        else:
            self._file_count_var.set(f"✅ 找到 {n} 个 RTL 文件")

    def _paste_log(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return
        if text:
            if getattr(self._log_text, "_has_placeholder", False):
                self._log_text.delete("1.0", tk.END)
                self._log_text._has_placeholder = False
                self._log_text.config(fg=TEXT)
            self._log_text.delete("1.0", tk.END)
            self._log_text.insert("1.0", text)
            self._log_text.config(fg=TEXT)
            self._log_text._has_placeholder = False

    def _clear_log(self) -> None:
        self._log_text._has_placeholder = False
        self._log_text.delete("1.0", tk.END)
        self._log_text.config(fg=TEXT)
        _make_placeholder(self._log_text, self._log_text._placeholder)

    def _copy_results(self) -> None:
        content = self._result_text.get("1.0", "end-1c")
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self._flash_status("✅ 已复制到剪贴板", SUCCESS)

    def _save_results(self) -> None:
        content = self._result_text.get("1.0", "end-1c")
        if not content or content.startswith("分析结果将在此处显示"):
            messagebox.showinfo("提示", "暂无分析结果可保存。")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="保存分析结果",
        )
        if path:
            Path(path).write_text(content, encoding="utf-8")
            self._flash_status(f"✅ 已保存至 {path}", SUCCESS)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _start_analysis(self) -> None:
        if self._analyzing:
            return

        # Validate inputs
        api_key = self._api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("缺少 API Key",
                                   "请填写 OpenAI API Key 后再开始分析。")
            return

        error_log = _get_text(self._log_text)
        if not error_log:
            messagebox.showwarning("日志为空", "请粘贴仿真工具的 Error Log。")
            return

        # Warn if no RTL files (but allow to proceed)
        if not self._rtl_files:
            if not messagebox.askyesno(
                "无 RTL 文件",
                "当前没有加载任何 RTL 文件，分析将在没有源码上下文的情况下进行。\n\n是否继续？",
            ):
                return

        self._set_analyzing(True)

        model = self._model_var.get().strip() or "gpt-4o"
        rtl_files = dict(self._rtl_files)

        # Run in background thread to keep UI responsive
        thread = threading.Thread(
            target=self._run_analysis_thread,
            args=(api_key, model, error_log, rtl_files),
            daemon=True,
        )
        thread.start()

    def _run_analysis_thread(
        self,
        api_key: str,
        model: str,
        error_log: str,
        rtl_files: dict[str, str],
    ) -> None:
        try:
            from eda_agent.analyzers.error_log_analyzer import ErrorLogAnalyzer
            from eda_agent.llm_client import LLMClient

            llm = LLMClient(model=model, api_key=api_key)
            analyzer = ErrorLogAnalyzer(llm_client=llm)
            result = analyzer.analyze(error_log=error_log, rtl_files=rtl_files)
            self.after(0, self._on_analysis_success, result.analysis)
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            self.after(0, self._on_analysis_error, str(exc))
        except Exception as exc:  # noqa: BLE001 — catch-all for unexpected LLM/network errors
            self.after(0, self._on_analysis_error, f"Unexpected error: {exc}")

    def _on_analysis_success(self, analysis: str) -> None:
        self._set_analyzing(False)
        self._display_result(analysis)
        self._flash_status("✅ 分析完成", SUCCESS)

    def _on_analysis_error(self, error_msg: str) -> None:
        self._set_analyzing(False)
        self._flash_status(f"❌ 分析失败", ERROR_CLR)
        messagebox.showerror("分析出错", f"分析时发生错误：\n\n{error_msg}")

    # ------------------------------------------------------------------
    # UI state helpers
    # ------------------------------------------------------------------

    def _set_analyzing(self, state: bool) -> None:
        self._analyzing = state
        if state:
            self._analyze_btn.config(text="⏳  分析中…", bg=SECONDARY)
            self._progress.pack(side="right", padx=(0, 12), pady=4)
            self._progress.start(12)
            self._flash_status("🔄 正在调用 LLM 分析…", PRIMARY)
        else:
            self._analyze_btn.config(text="🔍  开始分析", bg=PRIMARY)
            self._progress.stop()
            self._progress.pack_forget()

    def _flash_status(self, msg: str, color: str = SECONDARY) -> None:
        self._status_var.set(msg)
        self._status_lbl.config(fg=color)

    def _set_result_placeholder(self) -> None:
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", tk.END)
        self._result_text.insert(
            "1.0",
            "分析结果将在此处显示。\n\n"
            "请先：\n"
            "  1. 选择 RTL 工程目录\n"
            "  2. 粘贴仿真错误日志\n"
            "  3. 点击「🔍 开始分析」",
            "placeholder",
        )
        self._result_text.config(state="disabled")

    def _display_result(self, analysis: str) -> None:
        """Render the analysis text with simple formatting."""
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", tk.END)

        for line in analysis.splitlines():
            stripped = line.strip()
            # Detect section headers (lines starting with ##, ===, or ALL CAPS short)
            if stripped.startswith("##") or stripped.startswith("==="):
                cleaned = stripped.lstrip("#= ").strip()
                self._result_text.insert(tk.END, cleaned + "\n", "header")
            elif stripped and len(stripped) < 60 and stripped.isupper():
                self._result_text.insert(tk.END, stripped + "\n", "header")
            elif stripped.startswith("```") or stripped.startswith("~~~"):
                # Skip code-fence markers
                pass
            else:
                self._result_text.insert(tk.END, line + "\n", "body")

        self._result_text.config(state="disabled")
        self._result_text.see("1.0")

    def _on_close(self) -> None:
        if self._analyzing:
            if not messagebox.askyesno("确认退出", "分析正在进行中，确定要退出吗？"):
                return
        self.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # Add repo root to sys.path so eda_agent can be imported
    repo_root = Path(__file__).parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
