"""Reusable Tk widgets (moved verbatim from v2.8.0 main.py)."""

import tkinter as tk
from tkinter import ttk
from geodesync.ui.theme import UI



class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, bg=UI["lilac"], hover_bg=UI["lilac_dark"], fg=UI["text"], height=46, width=None, font=("Segoe UI", 11, "bold")):
        super().__init__(parent, height=height, width=width or 200, bg=parent["bg"], highlightthickness=2,
                         highlightbackground=parent["bg"], highlightcolor=UI["cyan"], takefocus=True)
        self.command = command
        self.normal_bg = bg
        self.hover_bg = hover_bg
        self.current_bg = bg
        self.fg = fg
        self.text = text
        self.font = font
        self.height = height
        self.btn_width = width
        self.wraplength = max(90, (width - 20) if width else 180)
        self.enabled = True

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.bind("<Return>", self.on_click)
        self.bind("<space>", self.on_click)
        self.bind("<FocusIn>", self.draw)
        self.bind("<FocusOut>", self.draw)
        self.bind("<Configure>", self.draw)

    def draw(self, event=None):
        self.delete("all")
        w = self.winfo_width() if not self.btn_width else self.btn_width
        h = self.height
        if not self.btn_width:
            self.wraplength = max(90, w - 20)
        r = 10

        if not self.enabled:
            fill = UI["border"]
            text_color = UI["quiet"]
        else:
            fill = self.current_bg
            text_color = self.fg

        self.create_arc((0, 0, r * 2, r * 2), start=90, extent=90, fill=fill, outline="")
        self.create_arc((w - r * 2, 0, w, r * 2), start=0, extent=90, fill=fill, outline="")
        self.create_arc((0, h - r * 2, r * 2, h), start=180, extent=90, fill=fill, outline="")
        self.create_arc((w - r * 2, h - r * 2, w, h), start=270, extent=90, fill=fill, outline="")
        self.create_rectangle((r, 0, w - r, h), fill=fill, outline="")
        self.create_rectangle((0, r, w, h - r), fill=fill, outline="")

        self.create_text(w / 2, h / 2, text=self.text, fill=text_color, font=self.font,
                         width=self.wraplength, justify="center")
        if self.focus_get() == self:
            self.create_rectangle(2, 2, max(2, w - 2), max(2, h - 2), outline=UI["cyan"], width=1)

    def on_enter(self, event):
        if self.enabled:
            self.current_bg = self.hover_bg
            self.draw()

    def on_leave(self, event):
        if self.enabled:
            self.current_bg = self.normal_bg
            self.draw()

    def on_click(self, event):
        if self.enabled and self.command:
            self.command()
            return "break"

    def invoke(self):
        if self.enabled and self.command:
            return self.command()
        return None

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self.draw()

    def configure(self, cnf=None, **kwargs):
        """Support the small, familiar subset of Tk Button options used by the app."""
        options = {}
        if isinstance(cnf, dict):
            options.update(cnf)
        elif isinstance(cnf, str):
            mapped = {"text": self.text, "fg": self.fg, "bg": self.normal_bg,
                      "activebackground": self.hover_bg, "command": self.command,
                      "state": "normal" if self.enabled else "disabled"}
            if cnf in mapped:
                return mapped[cnf]
            return super().configure(cnf)
        elif cnf is not None:
            return super().configure(cnf)
        options.update(kwargs)
        redraw = False
        for key in ("text", "fg", "bg", "activebackground", "hover_bg", "command", "font", "height", "state"):
            if key not in options:
                continue
            value = options.pop(key)
            if key == "text":
                self.text = value
            elif key == "fg":
                self.fg = value
            elif key == "bg":
                self.normal_bg = value
                self.current_bg = value
            elif key in ("activebackground", "hover_bg"):
                self.hover_bg = value
            elif key == "command":
                self.command = value
            elif key == "font":
                self.font = value
            elif key == "height":
                self.height = int(value)
                options["height"] = self.height
            elif key == "state":
                self.enabled = value not in ("disabled", tk.DISABLED)
            redraw = True
        result = super().configure(**options) if options else None
        if redraw and hasattr(self, "text"):
            self.draw()
        return result

    config = configure

    def cget(self, key):
        values = {"text": self.text, "fg": self.fg, "bg": self.normal_bg,
                  "activebackground": self.hover_bg, "command": self.command,
                  "state": "normal" if self.enabled else "disabled"}
        return values[key] if key in values else super().cget(key)

    def set_config(self, text: str, bg: str, hover_bg: str, command=None, fg=None):
        self.text = text
        self.normal_bg = bg
        self.hover_bg = hover_bg
        self.current_bg = bg
        if fg:
            self.fg = fg
        if command:
            self.command = command
        self.draw()


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg=UI["background"], *args, **kwargs):
        super().__init__(parent, bg=bg, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_content = tk.Frame(self.canvas, bg=bg)

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self._window_id = self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._window_id, width=e.width)
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            delta = int(-1 * (event.delta / 120)) if hasattr(event, "delta") and event.delta else (1 if getattr(event, "num", None) == 5 else -1)
            self.canvas.yview_scroll(delta, "units")

        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
