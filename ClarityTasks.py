import json, csv, os, datetime
from dataclasses import dataclass, asdict
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

# --------- Model ---------
DATA_FILE = "tasks.json"
DATE_FMT = "%Y-%m-%d"

@dataclass
class Task:
    title: str
    done: bool = False
    priority: str = "Medium"  # Low, Medium, High
    due: str | None = None    # YYYY-MM-DD or None
    created: str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def is_overdue(self) -> bool:
        if self.done or not self.due:
            return False
        try:
            d = datetime.datetime.strptime(self.due, DATE_FMT).date()
            return d < datetime.date.today()
        except ValueError:
            return False

    def is_due_today(self) -> bool:
        if self.done or not self.due:
            return False
        try:
            d = datetime.datetime.strptime(self.due, DATE_FMT).date()
            return d == datetime.date.today()
        except ValueError:
            return False


# --------- Storage ---------
def load_tasks() -> list[Task]:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        tasks = []
        for item in raw:
            # Backward compatibility & validation
            tasks.append(Task(
                title=item.get("title", ""),
                done=bool(item.get("done", False)),
                priority=item.get("priority", "Medium"),
                due=item.get("due"),
                created=item.get("created", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ))
        return tasks
    except Exception as e:
        messagebox.showerror("Load Error", f"Failed to read {DATA_FILE}:\n{e}")
        return []

def save_tasks(tasks: list[Task]) -> None:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([asdict(t) for t in tasks], f, indent=2, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to write {DATA_FILE}:\n{e}")


# --------- Controller / UI ---------
class TodoApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master: tk.Tk = master
        self.tasks: list[Task] = load_tasks()
        self.filtered_indices: list[int] = []  # map view rows -> self.tasks index
        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="All")
        self.title_var = tk.StringVar()
        self.priority_var = tk.StringVar(value="Medium")
        self.due_var = tk.StringVar()

        self._build_style()
        self._build_ui()
        self._bind_shortcuts()
        self.refresh_view()  # initial populate

    # ---- UI Pieces ----
    def _build_style(self):
        self.master.title("To-Do List — Pro")
        self.master.geometry("760x520")
        self.master.minsize(680, 460)
        self.master.configure(background="#f7f7fb")

        style = ttk.Style()
        try:
            self.master.call("tk", "scaling", 1.25)  # a touch larger on HiDPI
        except tk.TclError:
            pass
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("TFrame", background="#f7f7fb")
        style.configure("TLabel", background="#f7f7fb", font=("Segoe UI", 10))
        style.configure("TButton", padding=6, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 12))
        style.configure("Danger.TButton", foreground="#b00020")
        style.configure("Muted.TLabel", foreground="#555")
        style.configure("Done.Treeview", foreground="#6a6a6a")
        style.map("TButton", relief=[("pressed", "sunken"), ("!pressed", "raised")])

    def _build_ui(self):
        # Top: Add row
        add_row = ttk.Frame(self.master, padding=(12, 12, 12, 6))
        add_row.pack(fill="x")

        ttk.Label(add_row, text="Task").grid(row=0, column=0, sticky="w")
        title = ttk.Entry(add_row, textvariable=self.title_var, width=40)
        title.grid(row=1, column=0, padx=(0, 8), sticky="we")

        ttk.Label(add_row, text="Priority").grid(row=0, column=1, sticky="w")
        prio = ttk.Combobox(add_row, textvariable=self.priority_var, values=["Low", "Medium", "High"], width=10, state="readonly")
        prio.grid(row=1, column=1, padx=(0, 8), sticky="w")

        ttk.Label(add_row, text="Due (YYYY-MM-DD)").grid(row=0, column=2, sticky="w")
        due = ttk.Entry(add_row, textvariable=self.due_var, width=14)
        due.grid(row=1, column=2, padx=(0, 8), sticky="w")

        add_btn = ttk.Button(add_row, text="Add Task", command=self.add_task)
        add_btn.grid(row=1, column=3, padx=(0, 8))

        edit_btn = ttk.Button(add_row, text="Edit", command=self.edit_selected)
        edit_btn.grid(row=1, column=4, padx=(0, 8))

        toggle_btn = ttk.Button(add_row, text="Toggle Done (Ctrl+D)", command=self.toggle_selected)
        toggle_btn.grid(row=1, column=5, padx=(0, 8))

        del_btn = ttk.Button(add_row, text="Delete (Del)", style="Danger.TButton", command=self.delete_selected)
        del_btn.grid(row=1, column=6)

        add_row.grid_columnconfigure(0, weight=1)

        # Search / Filters
        ctrl_row = ttk.Frame(self.master, padding=(12, 0, 12, 6))
        ctrl_row.pack(fill="x")

        ttk.Label(ctrl_row, text="Search").grid(row=0, column=0, sticky="w")
        search = ttk.Entry(ctrl_row, textvariable=self.search_var)
        search.grid(row=1, column=0, padx=(0, 8), sticky="we")

        ttk.Label(ctrl_row, text="Filter").grid(row=0, column=1, sticky="w")
        filt = ttk.Combobox(
            ctrl_row, textvariable=self.filter_var,
            values=["All", "Active", "Completed", "Due Today", "Overdue", "High Priority"],
            width=16, state="readonly"
        )
        filt.grid(row=1, column=1, padx=(0, 8), sticky="w")

        export_btn = ttk.Button(ctrl_row, text="Export CSV", command=self.export_csv)
        export_btn.grid(row=1, column=2, padx=(0, 8))

        clear_done_btn = ttk.Button(ctrl_row, text="Clear Completed", command=self.clear_completed)
        clear_done_btn.grid(row=1, column=3)

        ctrl_row.grid_columnconfigure(0, weight=1)

        # Treeview (list)
        list_frame = ttk.Frame(self.master, padding=(12, 0, 12, 0))
        list_frame.pack(fill="both", expand=True)

        cols = ("title", "priority", "due", "status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("title", text="Task")
        self.tree.heading("priority", text="Priority")
        self.tree.heading("due", text="Due")
        self.tree.heading("status", text="Status")
        self.tree.column("title", width=380, anchor="w")
        self.tree.column("priority", width=90, anchor="center")
        self.tree.column("due", width=110, anchor="center")
        self.tree.column("status", width=110, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

        # Status bar
        status = ttk.Frame(self.master, padding=(12, 6, 12, 12))
        status.pack(fill="x")
        self.count_label = ttk.Label(status, text="", style="Muted.TLabel")
        self.count_label.pack(side="left")

        # Events
        self.search_var.trace_add("write", lambda *_: self.refresh_view())
        self.filter_var.trace_add("write", lambda *_: self.refresh_view())
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())
        self.tree.bind("<Button-3>", self._context_menu)

    def _bind_shortcuts(self):
        self.master.bind("<Return>", lambda e: self.add_task())
        self.master.bind("<Delete>", lambda e: self.delete_selected())
        self.master.bind("<Control-d>", lambda e: self.toggle_selected())
        self.master.bind("<Control-D>", lambda e: self.toggle_selected())
        self.master.bind("<Control-f>", lambda e: self._focus_search())

    # ---- Actions ----
    def _focus_search(self):
        for w in self.master.winfo_children():
            for child in w.winfo_children():
                if isinstance(child, ttk.Entry) and child is not None and child.cget("textvariable") == str(self.search_var):
                    child.focus_set()
                    child.selection_range(0, tk.END)
                    return

    def _context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(label="Toggle Done", command=self.toggle_selected)
        menu.add_command(label="Edit", command=self.edit_selected)
        menu.add_separator()
        menu.add_command(label="Delete", command=self.delete_selected)
        menu.tk_popup(event.x_root, event.y_root)

    def add_task(self):
        title = self.title_var.get().strip()
        prio = self.priority_var.get().strip() or "Medium"
        due = self.due_var.get().strip() or None

        if not title:
            messagebox.showwarning("Missing Title", "Please type a task.")
            return
        if due and not self._valid_date(due):
            messagebox.showwarning("Invalid Date", "Use YYYY-MM-DD (e.g., 2025-09-04).")
            return

        self.tasks.append(Task(title=title, priority=prio, due=due))
        save_tasks(self.tasks)
        self.title_var.set("")
        self.due_var.set("")
        self.priority_var.set("Medium")
        self.refresh_view()

    def edit_selected(self):
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo("Select Task", "Choose a task to edit.")
            return
        t = self.tasks[idx]
        new_title = simpledialog.askstring("Edit Task", "Title:", initialvalue=t.title, parent=self.master)
        if new_title is None:
            return
        new_title = new_title.strip() or t.title

        new_prio = simpledialog.askstring("Edit Task", "Priority (Low/Medium/High):", initialvalue=t.priority, parent=self.master)
        if new_prio is None:
            return
        new_prio = new_prio.capitalize()
        if new_prio not in ("Low", "Medium", "High"):
            messagebox.showwarning("Invalid Priority", "Use Low, Medium, or High.")
            return

        new_due = simpledialog.askstring("Edit Task", "Due (YYYY-MM-DD or empty):", initialvalue=t.due or "", parent=self.master)
        if new_due is None:
            return
        new_due = new_due.strip() or None
        if new_due and not self._valid_date(new_due):
            messagebox.showwarning("Invalid Date", "Use YYYY-MM-DD.")
            return

        t.title, t.priority, t.due = new_title, new_prio, new_due
        save_tasks(self.tasks)
        self.refresh_view()

    def toggle_selected(self):
        idx = self._selected_index()
        if idx is None:
            return
        self.tasks[idx].done = not self.tasks[idx].done
        save_tasks(self.tasks)
        self.refresh_view()

    def delete_selected(self):
        idx = self._selected_index()
        if idx is None:
            return
        title = self.tasks[idx].title
        if messagebox.askyesno("Delete", f"Delete task:\n\n{title}"):
            self.tasks.pop(idx)
            save_tasks(self.tasks)
            self.refresh_view()

    def clear_completed(self):
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if not t.done]
        if len(self.tasks) != before:
            save_tasks(self.tasks)
            self.refresh_view()

    def export_csv(self):
        if not self.tasks:
            messagebox.showinfo("Nothing to Export", "No tasks to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Export Tasks", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Title", "Done", "Priority", "Due", "Created"])
                for t in self.tasks:
                    w.writerow([t.title, "Yes" if t.done else "No", t.priority, t.due or "", t.created])
            messagebox.showinfo("Exported", f"Saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ---- Helpers ----
    def _valid_date(self, s: str) -> bool:
        try:
            datetime.datetime.strptime(s, DATE_FMT)
            return True
        except ValueError:
            return False

    def _selected_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        view_row = int(sel[0])
        if view_row < 0 or view_row >= len(self.filtered_indices):
            return None
        return self.filtered_indices[view_row]

    def _matches_filter(self, t: Task) -> bool:
        f = self.filter_var.get()
        if f == "All":
            return True
        if f == "Active":
            return not t.done
        if f == "Completed":
            return t.done
        if f == "Due Today":
            return t.is_due_today()
        if f == "Overdue":
            return t.is_overdue()
        if f == "High Priority":
            return t.priority == "High" and not t.done
        return True

    def _matches_search(self, t: Task) -> bool:
        q = self.search_var.get().strip().lower()
        if not q:
            return True
        hay = f"{t.title} {t.priority} {t.due or ''}".lower()
        return q in hay

    def refresh_view(self):
        # Clear
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        # Build filtered index map
        self.filtered_indices.clear()
        for i, t in enumerate(self.tasks):
            if self._matches_filter(t) and self._matches_search(t):
                self.filtered_indices.append(i)

        # Insert rows
        for row_idx, i in enumerate(self.filtered_indices):
            t = self.tasks[i]
            status = "Done" if t.done else ("Overdue" if t.is_overdue() else ("Due Today" if t.is_due_today() else "Pending"))
            values = (t.title, t.priority, t.due or "", status)
            self.tree.insert("", "end", iid=str(row_idx), values=values)

        # Status bar
        active = sum(1 for t in self.tasks if not t.done)
        self.count_label.config(text=f"{active} task(s) remaining — {len(self.tasks)} total")
        # Persist view changes (order isn't changed here, but if you add sorting later, save)
        save_tasks(self.tasks)


# --------- Run ---------
if __name__ == "__main__":
    root = tk.Tk()
    app = TodoApp(root)
    root.mainloop()
