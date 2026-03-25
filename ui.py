"""
主界面UI模块，负责窗口布局和交互
"""
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog
from data_manager import DataManager, BookManager, get_data_dir
from chart import ChartManager
import datetime
import os
import ctypes


def _enable_high_dpi_awareness():
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class ModernButton(tk.Canvas):
    def __init__(self, master, text, command, width=120, height=40,
                 radius=16, bg="#8D9C8B", hover_bg="#798A77", active_bg="#6A7A69",
                 fg="#F8F5F0", font=("Microsoft YaHei UI", 10), **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=master.cget("bg"),
            cursor="hand2",
            **kwargs
        )
        self._text = text
        self._command = command
        self._btn_width = width
        self._btn_height = height
        self._radius = radius
        self._colors = {
            "normal": bg,
            "hover": hover_bg,
            "active": active_bg,
            "fg": fg,
        }
        self._font = font
        self._anim_id = None
        self._current_color = bg
        self._draw_color(self._current_color)

        self.bind("<Enter>", lambda e: self._animate_to("hover"))
        self.bind("<Leave>", lambda e: self._animate_to("normal"))
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _rounded_points(self, x1, y1, x2, y2, r):
        return [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]

    def _hex_to_rgb(self, color):
        color = color.lstrip("#")
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _mix(self, c1, c2, t):
        r1, g1, b1 = self._hex_to_rgb(c1)
        r2, g2, b2 = self._hex_to_rgb(c2)
        mixed = (
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
        )
        return self._rgb_to_hex(mixed)

    def _draw_color(self, color):
        self.delete("all")
        self.create_polygon(
            self._rounded_points(2, 2, self._btn_width - 2, self._btn_height - 2, self._radius),
            smooth=True,
            splinesteps=36,
            fill=color,
            outline=""
        )
        self.create_text(
            self._btn_width / 2,
            self._btn_height / 2,
            text=self._text,
            fill=self._colors["fg"],
            font=self._font
        )

    def _animate_to(self, state, steps=6, duration=90):
        target = self._colors[state]
        if self._anim_id is not None:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        if target == self._current_color:
            return
        interval = max(10, duration // steps)

        def step(i=1):
            t = i / steps
            self._current_color = self._mix(self._current_color, target, t)
            self._draw_color(self._current_color)
            if i < steps:
                self._anim_id = self.after(interval, lambda: step(i + 1))
            else:
                self._current_color = target
                self._draw_color(self._current_color)
                self._anim_id = None

        step()

    def _on_press(self, _event):
        self._animate_to("active", steps=4, duration=50)

    def _on_release(self, event):
        self._animate_to("hover")
        if 0 <= event.x <= self._btn_width and 0 <= event.y <= self._btn_height:
            self._command()


class AnimatedCombobox(tk.Frame):
    _active_instance = None

    def __init__(self, master, textvariable, values=None, width=12, style=None, **kwargs):
        theme = kwargs.pop("theme", None)
        super().__init__(master, bg=master.cget("bg"), **kwargs)
        self.textvariable = textvariable
        self.values = list(values) if values is not None else []
        self.style = style
        self.width = width
        self.theme = theme or {}
        self._selected_callback = None
        self._postcommand = None
        self._open = False
        self._popup = None
        self._listbox = None
        self._popup_x = 0
        self._popup_y = 0
        self._popup_w = 0
        self._target_h = 0

        self._input_bg = self.theme.get("input_bg", "#F4EFE7")
        self._soft = self.theme.get("soft", "#D3C5B8")
        self._text = self.theme.get("text", "#4F4A45")
        self._selected_bg = self.theme.get("table_selected", "#B7C4AF")

        self.configure(highlightthickness=0, bd=1, relief="solid", highlightbackground=self._soft, bg=self._input_bg)
        # Entry 使用普通输入框样式，避免显示 Combobox 自带箭头导致重复按钮
        entry_style = "Morandi.TEntry" if self.style is None else self.style.replace("Combobox", "Entry")
        self.entry = ttk.Entry(self, textvariable=self.textvariable, width=self.width, style=entry_style, state="readonly")
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=3)
        self.arrow = tk.Label(
            self,
            text="▾",
            bg=self._input_bg,
            fg=self._text,
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "bold"),
            width=2,
            bd=0,
        )
        self.arrow.pack(side=tk.RIGHT, padx=(0, 4), pady=2)

        self.entry.bind("<Button-1>", self._on_click)
        self.arrow.bind("<Button-1>", self._on_click)

        top = self.winfo_toplevel()
        top.bind("<Button-1>", self._on_any_click, add="+")
        top.bind("<MouseWheel>", self._on_any_wheel, add="+")
        top.bind("<FocusOut>", self._on_top_focus_out, add="+")

    def _on_click(self, _event=None):
        self.toggle()
        return "break"

    def _is_widget_inside(self, widget, ancestor):
        current = widget
        while current is not None:
            if current == ancestor:
                return True
            current = getattr(current, "master", None)
        return False

    def _on_any_click(self, event):
        if not self._open:
            return
        if self._is_widget_inside(event.widget, self):
            return
        if self._popup and self._is_widget_inside(event.widget, self._popup):
            return
        self.close()

    def _on_any_wheel(self, event):
        if not self._open:
            return
        if not (self._popup and self._is_widget_inside(event.widget, self._popup)):
            self.close()

    def _on_top_focus_out(self, _event=None):
        if self._open:
            self.close()

    def set_values(self, values):
        self.values = list(values)

    def current(self, idx=None):
        if idx is None:
            return self.values.index(self.textvariable.get()) if self.textvariable.get() in self.values else -1
        if 0 <= idx < len(self.values):
            self.textvariable.set(self.values[idx])

    def get(self):
        return self.textvariable.get()

    def bind(self, sequence=None, func=None, add=None):
        if sequence == "<<ComboboxSelected>>":
            self._selected_callback = func
        return super().bind(sequence, func, add)

    def _on_select(self, event=None):
        if not self._listbox:
            return
        idx = self._listbox.curselection()
        if not idx:
            return
        item = self._listbox.get(idx)
        self.textvariable.set(item)
        self.close()
        if self._selected_callback:
            self._selected_callback(event)

    def _animate_open(self):
        if not self._popup:
            return
        current_height = self._popup.winfo_height()
        if current_height >= self._target_h:
            self._popup.geometry(f"{self._popup_w}x{self._target_h}+{self._popup_x}+{self._popup_y}")
            return
        remain = self._target_h - current_height
        step = max(14, remain // 2)
        new_h = min(self._target_h, current_height + step)
        self._popup.geometry(f"{self._popup_w}x{new_h}+{self._popup_x}+{self._popup_y}")
        self.after(8, self._animate_open)

    def _animate_close(self):
        if not self._popup:
            return
        current_height = self._popup.winfo_height()
        if current_height <= 2:
            self._destroy_popup()
            return
        step = max(14, current_height // 2)
        new_h = max(0, current_height - step)
        self._popup.geometry(f"{self._popup_w}x{new_h}+{self._popup_x}+{self._popup_y}")
        self.after(8, self._animate_close)

    def open(self):
        if self._open:
            return
        if AnimatedCombobox._active_instance and AnimatedCombobox._active_instance is not self:
            AnimatedCombobox._active_instance.close()
        if self._postcommand:
            try:
                self._postcommand()
            except Exception:
                pass

        self._open = True
        AnimatedCombobox._active_instance = self
        self._popup = tk.Toplevel(self)
        self._popup.overrideredirect(True)
        self._popup.attributes("-topmost", True)

        self._popup_x = self.winfo_rootx()
        self._popup_y = self.winfo_rooty() + self.winfo_height()
        self._popup_w = self.winfo_width()
        self._target_h = min(max(len(self.values), 1), 8) * 24
        self._popup.geometry(f"{self._popup_w}x0+{self._popup_x}+{self._popup_y}")

        # 使用更轻量的下拉列表样式，去掉多余箭头，仅保留滑块
        s = ttk.Style(self._popup)
        try:
            s.layout("Thin.Vertical.TScrollbar", [
                ("Vertical.Scrollbar.trough", {
                    "children": [
                        ("Vertical.Scrollbar.thumb", {"unit": "1", "sticky": "ns"})
                    ],
                    "sticky": "ns"
                })
            ])
            s.configure("Thin.Vertical.TScrollbar",
                        troughcolor=self._input_bg,
                        background=self._soft,
                        bordercolor=self._soft,
                        relief="flat",
                        gripcount=0,
                        width=8)
        except Exception:
            pass

        frame = tk.Frame(self._popup, bg=self._input_bg, bd=1, relief="solid", highlightthickness=1, highlightbackground=self._soft)
        frame.pack(fill=tk.BOTH, expand=True)

        self._listbox = tk.Listbox(
            frame,
            selectmode=tk.SINGLE,
            activestyle="none",
            font=("Microsoft YaHei UI", 10),
            bd=0,
            highlightthickness=0,
            bg=self._input_bg,
            fg=self._text,
            selectbackground=self._selected_bg,
            selectforeground=self._text,
            relief="flat",
            exportselection=False,
        )
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._listbox.yview, style="Thin.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=4)
        self._listbox.config(yscrollcommand=scrollbar.set)

        for item in self.values:
            self._listbox.insert(tk.END, item)

        pre_idx = self.current()
        if pre_idx >= 0:
            self._listbox.selection_set(pre_idx)
            self._listbox.see(pre_idx)

        self._listbox.bind("<<ListboxSelect>>", self._on_select)
        self._popup.bind("<FocusOut>", lambda e: self.close())
        self._popup.update_idletasks()
        self._animate_open()

    def close(self):
        if not self._open:
            return
        self._open = False
        self._animate_close()

    def _destroy_popup(self):
        if self._popup:
            self._popup.destroy()
        self._popup = None
        self._listbox = None
        if AnimatedCombobox._active_instance is self:
            AnimatedCombobox._active_instance = None

    def toggle(self):
        if self._open:
            self.close()
        else:
            self.open()

    def postcommand(self, func):
        self._postcommand = func


def run_app():
    _enable_high_dpi_awareness()
    books_dir = get_data_dir()

    def export_pdf_action():
        pdf_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF文件", "*.pdf")])
        if pdf_path:
            try:
                dm.export_pdf(pdf_path)
                status_var.set("PDF 导出成功")
                messagebox.showinfo("导出成功", f"PDF已保存到：{pdf_path}")
            except Exception as e:
                messagebox.showerror("导出失败", str(e))

    app = tk.Tk()
    app.title("Smart Account")
    app.geometry("1040x730")
    app.minsize(930, 650)
    app.tk.call("tk", "scaling", app.winfo_fpixels("1i") / 72.0)

    palette = {
        "bg": "#EEE8DF",
        "panel": "#E2D8CC",
        "panel_soft": "#E9E0D6",
        "soft": "#D3C5B8",
        "text": "#4F4A45",
        "text_muted": "#7A746E",
        "button": "#8D9C8B",
        "button_hover": "#798A77",
        "button_active": "#6A7A69",
        "input_bg": "#F4EFE7",
        "table_bg": "#FAF8F4",
        "table_selected": "#B7C4AF",
        "row_even": "#F3EDE5",
        "row_odd": "#FBF8F2",
        "row_hover": "#EAE2D8",
        "income": "#5A7B63",
        "expense": "#8A5E58",
        "chip_bg": "#D8CDC0",
    }

    app.configure(bg=palette["bg"])
    app.option_add("*Font", "{Microsoft YaHei UI} 10")
    app.option_add("*TCombobox*Listbox.font", "{Microsoft YaHei UI} 10")
    app.option_add("*TCombobox*Listbox.background", palette["input_bg"])
    app.option_add("*TCombobox*Listbox.foreground", palette["text"])
    app.option_add("*TCombobox*Listbox.selectBackground", palette["table_selected"])
    app.option_add("*TCombobox*Listbox.selectForeground", palette["text"])
    app.option_add("*TCombobox*Listbox.relief", "flat")
    app.option_add("*TCombobox*Listbox.borderWidth", 0)

    style = ttk.Style(app)
    style.theme_use("clam")
    style.configure("Morandi.TFrame", background=palette["bg"])
    style.configure(
        "Morandi.TLabel",
        background=palette["bg"],
        foreground=palette["text"],
        font=("Microsoft YaHei UI", 11),
    )
    style.configure(
        "Panel.TLabel",
        background=palette["panel"],
        foreground=palette["text"],
        font=("Microsoft YaHei UI", 11),
    )
    style.configure(
        "PanelTitle.TLabel",
        background=palette["panel"],
        foreground=palette["text"],
        font=("Microsoft YaHei UI", 11, "bold"),
    )
    style.configure(
        "Morandi.TEntry",
        fieldbackground=palette["input_bg"],
        foreground=palette["text"],
        bordercolor=palette["soft"],
        lightcolor=palette["soft"],
        darkcolor=palette["soft"],
        insertcolor=palette["text"],
        padding=8,
        font=("Microsoft YaHei UI", 11),
    )
    style.configure(
        "Morandi.TCombobox",
        fieldbackground=palette["input_bg"],
        background=palette["input_bg"],
        foreground=palette["text"],
        bordercolor=palette["soft"],
        lightcolor=palette["soft"],
        darkcolor=palette["soft"],
        arrowsize=14,
        padding=7,
        font=("Microsoft YaHei UI", 11),
    )
    style.map(
        "Morandi.TCombobox",
        fieldbackground=[("readonly", palette["input_bg"])],
        background=[("readonly", palette["input_bg"])],
        foreground=[("readonly", palette["text"])],
    )
    style.configure(
        "Morandi.Treeview",
        background=palette["table_bg"],
        fieldbackground=palette["table_bg"],
        foreground=palette["text"],
        bordercolor=palette["soft"],
        rowheight=33,
        font=("Microsoft YaHei UI", 11),
    )
    style.map(
        "Morandi.Treeview",
        background=[("selected", palette["table_selected"])],
        foreground=[("selected", palette["text"])],
    )
    style.configure(
        "Morandi.Treeview.Heading",
        background=palette["panel"],
        foreground=palette["text"],
        relief="flat",
        font=("Microsoft YaHei UI", 11, "bold"),
        padding=8,
    )

    def create_card(parent, title, expand=False):
        card = tk.Frame(
            parent,
            bg=palette["panel"],
            highlightthickness=1,
            highlightbackground=palette["soft"],
            bd=0,
        )
        card.pack(fill=tk.BOTH if expand else tk.X, expand=expand, padx=16, pady=7)
        ttk.Label(card, text=title, style="PanelTitle.TLabel").pack(anchor="w", padx=12, pady=(10, 2))
        inner = tk.Frame(card, bg=palette["panel"])
        inner.pack(fill=tk.BOTH if expand else tk.X, expand=expand, padx=10, pady=(4, 10))
        return inner

    header_frame = tk.Frame(app, bg=palette["bg"])
    header_frame.pack(fill=tk.X, padx=18, pady=(12, 2))
    tk.Label(
        header_frame,
        text="📒  Smart Account",
        bg=palette["bg"],
        fg=palette["text"],
        font=("Microsoft YaHei UI", 17, "bold"),
    ).pack(side=tk.LEFT)

    content_host = tk.Frame(app, bg=palette["bg"])
    content_host.pack(fill=tk.BOTH, expand=True)

    content_canvas = tk.Canvas(content_host, bg=palette["bg"], highlightthickness=0)
    content_scroll = ttk.Scrollbar(content_host, orient="vertical", command=content_canvas.yview)
    content_canvas.configure(yscrollcommand=content_scroll.set)
    content_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    content_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    content_frame = tk.Frame(content_canvas, bg=palette["bg"])
    content_window = content_canvas.create_window((0, 0), window=content_frame, anchor="nw")

    def _on_content_configure(_event=None):
        content_canvas.configure(scrollregion=content_canvas.bbox("all"))

    def _on_canvas_configure(event):
        content_canvas.itemconfigure(content_window, width=event.width)

    def _on_mousewheel(event):
        content_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _is_descendant(widget, target):
        if target is None:
            return False
        current = widget
        while current is not None:
            if current == target:
                return True
            current = getattr(current, "master", None)
        return False

    def _is_combobox_popdown(widget):
        if widget is None:
            return False
        # 下拉列表（系统或自定义）均使用 Listbox，避免外层页面误滚动。
        return widget.winfo_class() == "Listbox"

    def _close_combobox_popdowns():
        # 收起可能打开的下拉列表，避免出现多个下拉同时展开。
        for cb in (book_menu, chart_year_combo, date_combo, category_combo, filter_category_combo):
            try:
                if hasattr(cb, "close"):
                    cb.close()
                else:
                    cb.event_generate("<Escape>")
            except Exception:
                pass

    def _on_global_mousewheel(event):
        if _is_combobox_popdown(event.widget):
            return
        # 记录表区域由表格自身处理滚动，外层容器不再跟随滚动。
        if _is_descendant(event.widget, tree) or _is_descendant(event.widget, tree_scroll):
            return

        # 鼠标离开下拉后滚轮触发时，顺便收回下拉框，再滚动页面。
        _close_combobox_popdowns()
        _on_mousewheel(event)

    content_frame.bind("<Configure>", _on_content_configure)
    content_canvas.bind("<Configure>", _on_canvas_configure)
    content_canvas.bind_all("<MouseWheel>", _on_global_mousewheel)

    stats_wrap = create_card(content_frame, "本账本概览")
    stat_income_var = tk.StringVar(value="收入 0.00")
    stat_expense_var = tk.StringVar(value="支出 0.00")
    stat_balance_var = tk.StringVar(value="结余 0.00")

    def build_stat_chip(master, var, fg):
        chip = tk.Label(
            master,
            textvariable=var,
            bg=palette["chip_bg"],
            fg=fg,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=12,
            pady=6,
        )
        chip.pack(side=tk.LEFT, padx=6)

    build_stat_chip(stats_wrap, stat_income_var, palette["income"])
    build_stat_chip(stats_wrap, stat_expense_var, palette["expense"])
    build_stat_chip(stats_wrap, stat_balance_var, palette["text"])

    book_mgr = BookManager(data_path=books_dir)
    current_book_var = tk.StringVar(value=book_mgr.current_book)
    dm = DataManager(data_path=books_dir, book_file=book_mgr.current_book)
    status_var = tk.StringVar(value="就绪")

    sort_state = {"日期": False, "类别": False, "金额": False, "备注": False}
    hover_item = {"iid": ""}
    tree = None
    tree_scroll = None

    def update_stats(source_df):
        income = 0.0
        expense = 0.0
        for _, row in source_df.iterrows():
            amount = float(row["金额"])
            if str(row["类别"]).strip() == "收入":
                income += amount
            else:
                expense += abs(amount)
        stat_income_var.set(f"收入 {income:.2f}")
        stat_expense_var.set(f"支出 {expense:.2f}")
        stat_balance_var.set(f"结余 {income - expense:.2f}")

    def render_records(source_df, status_text=None):
        for i in tree.get_children():
            tree.delete(i)
        for row_index, (idx, row) in enumerate(source_df.iterrows()):
            raw_amount = row["金额"]
            try:
                amount = float(raw_amount)
            except (ValueError, TypeError):
                # 当数据异常（如错误写入了“奶茶”在金额列）时，兜底为0.00并保持行可见
                amount = 0.0
            row_tag = "even" if row_index % 2 == 0 else "odd"
            amount_tag = "income" if str(row["类别"]).strip() == "收入" else "expense"
            tree.insert(
                "",
                "end",
                iid=idx,
                values=(row["日期"], row["类别"], f"{amount:.2f}", row["备注"]),
                tags=(row_tag, amount_tag),
            )

        # 小数据量时自动增大可见行，避免首屏被截断；大数据量保持滚动浏览。
        visible_rows = min(max(len(source_df), 10), 14)
        tree.configure(height=visible_rows)

        update_stats(source_df)
        if status_text is None:
            status_var.set(f"当前记录 {len(source_df)} 条")
        else:
            status_var.set(status_text)
        app.after_idle(_on_content_configure)

    def apply_filters(status_hint="已应用筛选"):
        cat = filter_category_var.get()
        keyword = search_var.get().strip().lower()
        df = dm.get_records(category=cat) if cat else dm.df
        if keyword:
            df = df[
                df.apply(
                    lambda row: keyword in str(row["日期"]).lower()
                    or keyword in str(row["类别"]).lower()
                    or keyword in str(row["备注"]).lower(),
                    axis=1,
                )
            ]
        render_records(df, f"{status_hint}，共 {len(df)} 条")

    def refresh_books():
        book_menu.set_values(book_mgr.list_books())
        current_book_var.set(book_mgr.current_book)

    def get_year_options():
        if dm.df.empty:
            return ["全部"]
        temp = dm.df.copy()
        temp["日期"] = temp["日期"].astype(str)
        years = sorted({d[:4] for d in temp["日期"] if len(d) >= 4 and d[:4].isdigit()}, reverse=True)
        return ["全部"] + years

    def refresh_chart_year_options():
        options = get_year_options()
        chart_year_combo.set_values(options)
        if chart_year_var.get() not in options:
            chart_year_var.set("全部")

    def switch_book(event=None):
        try:
            book_mgr.switch_book(current_book_var.get().replace(".csv", ""))
            dm.__init__(data_path=books_dir, book_file=book_mgr.current_book)
            refresh_chart_year_options()
            render_records(dm.df, f"已切换到账本：{book_mgr.current_book.replace('.csv', '')}")
        except Exception as e:
            messagebox.showerror("账本切换失败", str(e))

    def new_book():
        name = new_book_var.get().strip()
        if name:
            try:
                book_mgr.new_book(name)
                refresh_books()
                switch_book()
                new_book_var.set("")
                status_var.set(f"已新建账本：{name}")
                messagebox.showinfo("新建账本", f"账本 {name} 创建成功！")
            except Exception as e:
                messagebox.showerror("新建账本失败", str(e))

    def delete_book():
        name = current_book_var.get().replace(".csv", "")
        if name:
            confirm = messagebox.askyesno("确认删除", f"确定要删除账本 {name} 吗？此操作不可恢复！")
            if not confirm:
                return
            try:
                book_mgr.delete_book(name)
                refresh_books()
                switch_book()
                status_var.set(f"已删除账本：{name}")
                messagebox.showinfo("删除账本", f"账本 {name} 已删除！")
            except Exception as e:
                messagebox.showerror("删除账本失败", str(e))

    book_frame = create_card(content_frame, "账本管理")
    book_top = tk.Frame(book_frame, bg=palette["panel"])
    book_top.pack(fill=tk.X, pady=(0, 6))
    book_bottom = tk.Frame(book_frame, bg=palette["panel"])
    book_bottom.pack(fill=tk.X)

    ttk.Label(book_top, text="📚 账本:", style="Panel.TLabel").pack(side=tk.LEFT, padx=(0, 8))
    book_menu = AnimatedCombobox(book_top, textvariable=current_book_var, values=book_mgr.list_books(), width=18, style="Morandi.TCombobox", theme=palette)
    book_menu.pack(side=tk.LEFT, padx=(0, 8))
    book_menu.bind("<<ComboboxSelected>>", switch_book)

    new_book_var = tk.StringVar()
    ttk.Entry(book_top, textvariable=new_book_var, width=14, style="Morandi.TEntry").pack(side=tk.LEFT, padx=(0, 10))

    ModernButton(
        book_bottom,
        text="+ 新建",
        command=new_book,
        width=104,
        height=36,
        radius=14,
        bg=palette["button"],
        hover_bg=palette["button_hover"],
        active_bg=palette["button_active"],
    ).pack(side=tk.LEFT, padx=(0, 6))
    ModernButton(
        book_bottom,
        text="删除",
        command=delete_book,
        width=104,
        height=36,
        radius=14,
        bg="#A18E85",
        hover_bg="#8E7C73",
        active_bg="#7D6C63",
    ).pack(side=tk.LEFT, padx=(0, 6))
    ModernButton(
        book_bottom,
        text="↗ 导出PDF",
        command=export_pdf_action,
        width=110,
        height=36,
        radius=14,
        bg="#8C9A9A",
        hover_bg="#788786",
        active_bg="#687776",
    ).pack(side=tk.RIGHT, padx=2)
    refresh_books()

    def show_trend_chart():
        year_text = chart_year_var.get()
        year = int(year_text) if year_text.isdigit() else None
        ChartManager(dm.df).show_trend(year=year)

    def show_category_pie():
        ChartManager(dm.df).show_category_pie()

    def export_trend_png():
        year_text = chart_year_var.get()
        year = int(year_text) if year_text.isdigit() else None
        img_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG图片", "*.png")])
        if not img_path:
            return
        try:
            ChartManager(dm.df).save_trend(img_path, year=year)
            status_var.set(f"趋势图已导出：{img_path}")
            messagebox.showinfo("导出成功", f"趋势图已保存到：{img_path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def export_pie_png():
        img_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG图片", "*.png")])
        if not img_path:
            return
        try:
            ChartManager(dm.df).save_category_pie(img_path)
            status_var.set(f"饼图已导出：{img_path}")
            messagebox.showinfo("导出成功", f"饼图已保存到：{img_path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    chart_frame = create_card(content_frame, "图表分析")
    chart_year_var = tk.StringVar(value="全部")
    chart_control_frame = tk.Frame(chart_frame, bg=palette["panel"])
    chart_control_frame.pack(fill=tk.X, padx=2, pady=2)

    ttk.Label(chart_control_frame, text="年份:", style="Panel.TLabel").pack(side=tk.LEFT, padx=(0, 8))
    chart_year_combo = AnimatedCombobox(chart_control_frame, textvariable=chart_year_var, values=["全部"], width=10, style="Morandi.TCombobox", theme=palette)
    chart_year_combo.pack(side=tk.LEFT, padx=(0, 10))

    chart_buttons_frame = tk.Frame(chart_control_frame, bg=palette["panel"])
    chart_buttons_frame.pack(side=tk.LEFT, padx=(0, 6), pady=1)

    ModernButton(
        chart_buttons_frame,
        text="📈 趋势图",
        command=show_trend_chart,
        width=120,
        height=36,
        radius=14,
        bg="#8A9B90",
        hover_bg="#75887D",
        active_bg="#66796F",
    ).pack(side=tk.LEFT, padx=5)
    ModernButton(
        chart_buttons_frame,
        text="◔ 饼图",
        command=show_category_pie,
        width=110,
        height=36,
        radius=14,
        bg="#9AA28D",
        hover_bg="#858F79",
        active_bg="#727D67",
    ).pack(side=tk.LEFT, padx=5)
    ModernButton(
        chart_buttons_frame,
        text="⤓ 导出趋势图",
        command=export_trend_png,
        width=128,
        height=36,
        radius=14,
        bg="#8C9A9A",
        hover_bg="#788786",
        active_bg="#687776",
    ).pack(side=tk.LEFT, padx=5)
    ModernButton(
        chart_buttons_frame,
        text="⤓ 导出饼图",
        command=export_pie_png,
        width=128,
        height=36,
        radius=14,
        bg="#8C9A9A",
        hover_bg="#788786",
        active_bg="#687776",
    ).pack(side=tk.LEFT, padx=5)
    refresh_chart_year_options()

    form_frame = create_card(content_frame, "新增记录")
    form_top = tk.Frame(form_frame, bg=palette["panel"])
    form_top.pack(fill=tk.X)
    form_bottom = tk.Frame(form_frame, bg=palette["panel"])
    form_bottom.pack(fill=tk.X, pady=(6, 0))

    ttk.Label(form_top, text="📅 日期:", style="Panel.TLabel").grid(row=0, column=0, padx=(0, 6), pady=4)
    date_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))

    def update_date(*args):
        date_var.set(date_combo.get())

    date_list = [(datetime.date.today() - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(0, 365)]
    date_combo = AnimatedCombobox(form_top, textvariable=date_var, values=date_list, width=12, style="Morandi.TCombobox", theme=palette)
    date_combo.grid(row=0, column=1, padx=(0, 10), pady=4)
    date_combo.bind("<<ComboboxSelected>>", update_date)

    ttk.Label(form_top, text="🏷 类别:", style="Panel.TLabel").grid(row=0, column=2, padx=(0, 6), pady=4)
    common_categories = ["餐饮", "购物", "交通", "学习", "娱乐", "通讯", "健康", "社交", "其他", "收入"]
    category_var = tk.StringVar()
    category_combo = AnimatedCombobox(form_top, textvariable=category_var, values=common_categories, width=12, style="Morandi.TCombobox", theme=palette)
    category_combo.grid(row=0, column=3, padx=(0, 10), pady=4)

    ttk.Label(form_top, text="￥ 金额:", style="Panel.TLabel").grid(row=0, column=4, padx=(0, 6), pady=4)
    amount_var = tk.StringVar()
    ttk.Entry(form_top, textvariable=amount_var, width=10, style="Morandi.TEntry").grid(row=0, column=5, padx=(0, 10), pady=4)

    ttk.Label(form_bottom, text="✎ 备注:", style="Panel.TLabel").grid(row=0, column=0, padx=(0, 6), pady=4)
    remark_var = tk.StringVar()
    ttk.Entry(form_bottom, textvariable=remark_var, width=46, style="Morandi.TEntry").grid(row=0, column=1, padx=(0, 10), pady=4, sticky="ew")
    form_bottom.columnconfigure(1, weight=1)

    def add_record():
        try:
            date = date_var.get()
            category = category_var.get().strip()
            if not category:
                messagebox.showwarning("类别必填", "请先选择类别！")
                return
            amount = float(amount_var.get())
            remark = remark_var.get()
            dm.add_record(date, category, amount, remark)
            date_var.set(datetime.date.today().strftime("%Y-%m-%d"))
            amount_var.set("")
            remark_var.set("")
            category_var.set("")
            apply_filters("记录添加成功")
            messagebox.showinfo("添加成功", "记录已添加！")
        except Exception as e:
            messagebox.showerror("添加失败", str(e))

    app.bind("<Return>", lambda e: add_record())

    ModernButton(
        form_bottom,
        text="+ 添加记录",
        command=add_record,
        width=110,
        height=36,
        radius=14,
        bg="#899A8D",
        hover_bg="#74887B",
        active_bg="#63766A",
    ).grid(row=0, column=2, padx=6, pady=2)

    list_frame = create_card(content_frame, "记录列表", expand=True)

    # 记录列表外框与上方模块保持一致对齐。
    list_frame.master.pack_configure(padx=16)

    # 表格显示区与滚动区缩窄到约 90%，视觉更聚焦。
    table_wrap = tk.Frame(list_frame, bg=palette["panel"])
    table_wrap.pack(fill=tk.BOTH, expand=True, padx=26)

    columns = ("日期", "类别", "金额", "备注")
    tree = ttk.Treeview(table_wrap, columns=columns, show="headings", style="Morandi.Treeview")
    tree.tag_configure("even", background=palette["row_even"])
    tree.tag_configure("odd", background=palette["row_odd"])
    tree.tag_configure("hover", background=palette["row_hover"])
    tree.tag_configure("income", foreground=palette["income"])
    tree.tag_configure("expense", foreground=palette["expense"])

    def sort_by_column(column_name):
        reverse = sort_state[column_name]
        rows = [(tree.set(k, column_name), k) for k in tree.get_children("")]
        if column_name == "金额":
            rows.sort(key=lambda item: float(item[0]), reverse=reverse)
        else:
            rows.sort(key=lambda item: item[0], reverse=reverse)
        for idx, (_, iid) in enumerate(rows):
            tree.move(iid, "", idx)
        sort_state[column_name] = not reverse
        status_var.set(f"已按 {column_name} {'降序' if reverse else '升序'} 排序")

    for col in columns:
        tree.heading(col, text=col, anchor="center", command=lambda c=col: sort_by_column(c))
        if col == "日期":
            tree.column(col, width=144, anchor="center")
        elif col == "类别":
            tree.column(col, width=144, anchor="center")
        elif col == "金额":
            tree.column(col, width=108, anchor="center")
        else:
            tree.column(col, width=270, anchor="center")

    tree_scroll = ttk.Scrollbar(table_wrap, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=tree_scroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def on_tree_motion(event):
        current = tree.identify_row(event.y)
        previous = hover_item["iid"]
        if previous and previous != current and tree.exists(previous):
            old_tags = tuple(tag for tag in tree.item(previous, "tags") if tag != "hover")
            tree.item(previous, tags=old_tags)
        if current and tree.exists(current):
            tags = tree.item(current, "tags")
            if "hover" not in tags:
                tree.item(current, tags=tuple(tags) + ("hover",))
        hover_item["iid"] = current

    def on_tree_leave(_event):
        previous = hover_item["iid"]
        if previous and tree.exists(previous):
            old_tags = tuple(tag for tag in tree.item(previous, "tags") if tag != "hover")
            tree.item(previous, tags=old_tags)
        hover_item["iid"] = ""

    tree.bind("<Motion>", on_tree_motion)
    tree.bind("<Leave>", on_tree_leave)

    def delete_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请选择要删除的记录")
            return
        try:
            idx_list = [int(i) for i in selected]
            dm.batch_delete(idx_list)
            apply_filters(f"删除成功，已删除 {len(idx_list)} 条")
            messagebox.showinfo("删除成功", f"已删除 {len(idx_list)} 条记录！")
        except Exception as e:
            messagebox.showerror("删除失败", str(e))

    action_bar = tk.Frame(content_frame, bg=palette["bg"])
    action_bar.pack(fill=tk.X, padx=16, pady=(0, 6), before=list_frame.master)

    toolbar = tk.Frame(
        action_bar,
        bg=palette["panel_soft"],
        highlightthickness=1,
        highlightbackground=palette["soft"],
        bd=0,
    )
    toolbar.pack(fill=tk.X)

    left_group = tk.Frame(toolbar, bg=palette["panel_soft"])
    left_group.pack(side=tk.LEFT, padx=(10, 8), pady=8)
    ModernButton(
        left_group,
        text="删除选中",
        command=delete_selected,
        width=136,
        height=38,
        radius=15,
        bg="#9E8A86",
        hover_bg="#8B7773",
        active_bg="#7A6864",
    ).pack(side=tk.LEFT, pady=2)

    tk.Frame(toolbar, bg=palette["soft"], width=1).pack(side=tk.LEFT, fill=tk.Y, pady=10, padx=(6, 10))

    filter_frame = tk.Frame(toolbar, bg=palette["panel_soft"])
    filter_frame.pack(side=tk.LEFT, padx=(0, 10), pady=8)
    tk.Label(
        filter_frame,
        text="⌕ 筛选类别:",
        bg=palette["panel_soft"],
        fg=palette["text"],
        font=("Microsoft YaHei UI", 10),
    ).pack(side=tk.LEFT, padx=(0, 8), pady=4)
    filter_category_var = tk.StringVar()
    filter_category_combo = AnimatedCombobox(filter_frame, textvariable=filter_category_var, values=common_categories, width=10, style="Morandi.TCombobox", theme=palette)
    filter_category_combo.pack(side=tk.LEFT, padx=(0, 10), pady=4)

    tk.Label(
        filter_frame,
        text="检索:",
        bg=palette["panel_soft"],
        fg=palette["text"],
        font=("Microsoft YaHei UI", 10),
    ).pack(side=tk.LEFT, padx=(0, 6), pady=4)
    search_var = tk.StringVar()
    search_entry = ttk.Entry(filter_frame, textvariable=search_var, width=17, style="Morandi.TEntry")
    search_entry.pack(side=tk.LEFT, padx=(0, 10), pady=4)

    def clear_filters():
        filter_category_var.set("")
        search_var.set("")
        render_records(dm.df, "已重置筛选")

    def on_search_changed(_event=None):
        apply_filters("搜索中")

    search_entry.bind("<KeyRelease>", on_search_changed)
    filter_category_combo.bind("<<ComboboxSelected>>", lambda _e: apply_filters())

    ModernButton(
        filter_frame,
        text="筛选",
        command=apply_filters,
        width=76,
        height=34,
        radius=13,
        bg="#8E9A93",
        hover_bg="#7A8680",
        active_bg="#69746F",
    ).pack(side=tk.LEFT, padx=(0, 6), pady=2)
    ModernButton(
        filter_frame,
        text="重置",
        command=clear_filters,
        width=76,
        height=34,
        radius=13,
        bg="#A19486",
        hover_bg="#8F8174",
        active_bg="#7E7165",
    ).pack(side=tk.LEFT, padx=(0, 2), pady=2)

    def toggle_fullscreen(event=None):
        is_fs = app.attributes("-fullscreen")
        app.attributes("-fullscreen", not is_fs)

    app.bind("<F11>", toggle_fullscreen)
    app.bind("<Escape>", lambda e: app.attributes("-fullscreen", False))
    app.bind("<Control-f>", lambda e: search_entry.focus_set())
    app.bind("<Control-r>", lambda e: clear_filters())
    app.bind("<Control-e>", lambda e: export_pdf_action())

    # 启动时自动重置筛选框，确保每次启动或切换账本后都是空白状态
    clear_filters()

    status_bar = tk.Label(
        app,
        textvariable=status_var,
        bg=palette["panel_soft"],
        fg=palette["text_muted"],
        font=("Microsoft YaHei UI", 10),
        anchor="w",
        padx=12,
        pady=6,
    )
    status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    render_records(dm.df)

    app.attributes("-alpha", 0.0)

    def fade_in(alpha=0.0):
        alpha += 0.08
        if alpha >= 1.0:
            app.attributes("-alpha", 1.0)
            return
        app.attributes("-alpha", alpha)
        app.after(18, lambda: fade_in(alpha))

    fade_in()
    app.mainloop()
