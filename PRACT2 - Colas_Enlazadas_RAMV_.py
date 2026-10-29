"""
COLA DE PEDIDOS (FIFO) con LISTA ENLAZADA + interfaz gráfica
=============================================================

Cómo ejecutarlo (no hay que instalar nada, tkinter viene con Python):

    python cola_pedidos.py            -> abre la ventana (interfaz gráfica)
    python cola_pedidos.py --test     -> ejecuta la prueba por consola (como TestQueue.java)

Clases (mismos nombres que en el enunciado):
    Order, Node, QueueInterface, LinkedQueue (la "Queue" del ejercicio)

REGLAS DE ENTRADA
    Cliente : solo letras (con tildes y ñ) y espacios entre palabras. Máximo 20 caracteres.
    Cantidad: solo números enteros de 1 a 1.000.000.
    Las cajas de texto ni siquiera dejan escribir algo que no cumpla las reglas.

NOTA: las posiciones se cuentan desde 1 (el primero de la cola es la posición 1).
"""

import io
import re
import sys
import unicodedata
from abc import ABC, abstractmethod
from contextlib import redirect_stdout

# ----------------------------------------------------------------------------
# LÍMITES (para que nadie rompa el programa metiendo cosas absurdas)
# ----------------------------------------------------------------------------
MAX_NAME_LEN = 20          # longitud máxima del nombre del cliente
MAX_QTTY = 1_000_000       # cantidad máxima por pedido
MAX_QUEUE_SIZE = 200       # número máximo de pedidos en la cola


def fmt_num(n):
    """1000000 -> '1.000.000'"""
    return f"{n:,}".replace(",", ".")


# ----------------------------------------------------------------------------
# VALIDACIÓN DE ENTRADAS (compartida por la interfaz y por la clase Order)
# ----------------------------------------------------------------------------
def is_letter(ch):
    """True si es una letra del alfabeto latino (incluye tildes, ñ, ü...)."""
    return ch.isalpha() and "LATIN" in unicodedata.name(ch, "")


def name_typing_error(text):
    """
    Se usa MIENTRAS se escribe. Devuelve un mensaje si el texto NO es válido, o None si lo es.
    Permite un espacio al final (porque la persona aún está escribiendo).
    """
    for ch in text:
        if ch != " " and not is_letter(ch):
            return "En el nombre solo se permiten letras (sin números, símbolos ni emojis)."
    if text.startswith(" "):
        return "El nombre no puede empezar con un espacio."
    if "  " in text:
        return "No pongas dos espacios seguidos."
    if len(text) > MAX_NAME_LEN:
        return f"Máximo {MAX_NAME_LEN} caracteres: el nombre ya no admite más letras."
    return None


def qtty_typing_error(text):
    """Igual que name_typing_error pero para la cantidad."""
    if text == "":
        return None
    if not (text.isascii() and text.isdigit()):
        return "En la cantidad solo se permiten números enteros (sin letras, signos, puntos ni espacios)."
    if text[0] == "0":
        return "La cantidad no puede empezar por 0."
    if len(text) > len(str(MAX_QTTY)) or int(text) > MAX_QTTY:
        return f"El máximo permitido es {fmt_num(MAX_QTTY)}."
    return None


def pos_typing_error(text):
    """Igual, para la posición (solo números, máximo 3 dígitos porque la cola admite 200)."""
    if text == "":
        return None
    if not (text.isascii() and text.isdigit()):
        return "En la posición solo se permiten números enteros."
    if text[0] == "0":
        return "Las posiciones empiezan en 1."
    if len(text) > len(str(MAX_QUEUE_SIZE)):
        return f"Máximo {len(str(MAX_QUEUE_SIZE))} dígitos: la cola admite hasta {MAX_QUEUE_SIZE} pedidos."
    return None


def clean_customer(text):
    """Validación FINAL del cliente. Devuelve el nombre limpio o lanza ValueError con un mensaje claro."""
    if not isinstance(text, str):
        raise ValueError("El nombre del cliente debe ser texto.")
    text = unicodedata.normalize("NFC", text).strip()
    if not text:
        raise ValueError("Escribe el nombre del cliente (no puede estar vacío).")
    if any(ch != " " and not is_letter(ch) for ch in text):
        raise ValueError("El nombre solo puede tener letras (sin números, símbolos, emojis "
                         "ni saltos de línea).")
    text = " ".join(text.split())  # "Ana    Pérez" -> "Ana Pérez"
    if len(text) > MAX_NAME_LEN:
        raise ValueError(f"El nombre es demasiado largo ({len(text)} caracteres). "
                         f"Máximo: {MAX_NAME_LEN}.")
    return text


def parse_positive_int(text, label, max_value):
    """
    Convierte un texto en un entero entre 1 y max_value.
    `label` es algo como "la cantidad" o "la posición".
    Lanza ValueError con un mensaje claro si algo está mal.
    """
    cap = label[0].upper() + label[1:]
    text = text.strip() if isinstance(text, str) else ""
    if not text:
        raise ValueError(f"Escribe {label}.")
    if re.fullmatch(r"[-−–]\s*\d+([.,]\d+)?", text):
        raise ValueError(f"{cap} no puede ser negativa ni cero: tiene que ser un número entero mayor que 0.")
    if re.fullmatch(r"\d+[.,]\d+", text, re.ASCII):
        raise ValueError(f"{cap} tiene que ser un número entero, sin decimales.")
    if not re.fullmatch(r"\d+", text, re.ASCII):
        raise ValueError(f"{cap} solo puede contener números enteros "
                         f"(sin letras, espacios ni símbolos).")
    digits = text.lstrip("0")
    if digits == "":
        raise ValueError(f"{cap} tiene que ser mayor que 0.")
    if len(digits) > len(str(max_value)) or int(digits) > max_value:
        raise ValueError(f"{cap} es demasiado grande (máximo permitido: {fmt_num(max_value)}).")
    return int(digits)


# ----------------------------------------------------------------------------
# CLASE Order (pedido)
# ----------------------------------------------------------------------------
class Order:
    def __init__(self, qtty, customer):
        if isinstance(qtty, bool) or not isinstance(qtty, int):
            raise ValueError("La cantidad debe ser un número entero.")
        if not 1 <= qtty <= MAX_QTTY:
            raise ValueError(f"La cantidad debe estar entre 1 y {fmt_num(MAX_QTTY)}.")
        self._customer = clean_customer(customer)
        self._qtty = qtty

    def print(self):
        print("     Customer: " + self.getCustomer())
        print("     Quantity: " + str(self.getQtty()))
        print("     ------------")

    def getQtty(self):
        return self._qtty

    def getCustomer(self):
        return self._customer


# ----------------------------------------------------------------------------
# CLASE Node (nodo de la lista enlazada)
# ----------------------------------------------------------------------------
class Node:
    def __init__(self, info, next_node=None):
        self.info = info        # el objeto que guarda el nodo
        self.next = next_node   # el nodo siguiente (None si es el último)

    def getInfo(self):
        return self.info

    def getNext(self):
        return self.next

    def setNext(self, node):
        self.next = node


# ----------------------------------------------------------------------------
# INTERFAZ QueueInterface
# ----------------------------------------------------------------------------
class QueueInterface(ABC):
    @abstractmethod
    def size(self): ...          # número de elementos

    @abstractmethod
    def isEmpty(self): ...       # True si está vacía

    @abstractmethod
    def front(self): ...         # primer elemento SIN quitarlo (None si vacía)

    @abstractmethod
    def enqueue(self, info): ... # añade al final

    @abstractmethod
    def dequeue(self): ...       # devuelve y QUITA el primero (None si vacía)


# ----------------------------------------------------------------------------
# CLASE LinkedQueue (la "Queue" del ejercicio)
# ----------------------------------------------------------------------------
class LinkedQueue(QueueInterface):
    def __init__(self):
        self.top = None     # cabeza: por aquí SALEN los elementos
        self.tail = None    # final: por aquí ENTRAN los elementos
        self._size = 0

    def size(self):
        return self._size

    def isEmpty(self):
        return self._size == 0

    def front(self):
        return None if self.top is None else self.top.getInfo()

    def getTail(self):
        """Devuelve el ÚLTIMO elemento sin quitarlo (None si la cola está vacía). Cuesta O(1) gracias a tail."""
        return None if self.tail is None else self.tail.getInfo()

    def enqueue(self, info):
        if info is None:
            raise ValueError("No se puede añadir 'nada' (None) a la cola.")
        if self._size >= MAX_QUEUE_SIZE:
            raise OverflowError(f"La cola está llena (máximo {MAX_QUEUE_SIZE} pedidos).")
        new_node = Node(info)
        if self.tail is None:           # cola vacía: el nuevo nodo es cabeza y final
            self.top = new_node
        else:                           # si no, se enlaza detrás del último
            self.tail.setNext(new_node)
        self.tail = new_node
        self._size += 1

    def dequeue(self):
        if self.top is None:
            return None
        info = self.top.getInfo()
        self.top = self.top.getNext()   # se desenlaza la cabeza
        if self.top is None:            # ¡ojo! si queda vacía, tail también debe ser None
            self.tail = None
        self._size -= 1
        return info

    def getNth(self, pos):
        """Devuelve el elemento en la posición pos (1 = primero) sin borrarlo. None si no es válida."""
        if isinstance(pos, bool) or not isinstance(pos, int):
            return None
        if pos < 1 or pos > self._size:
            return None
        node = self.top
        for _ in range(pos - 1):
            node = node.getNext()
        return node.getInfo()

    # --- extras ---
    def clear(self):
        self.top = None
        self.tail = None
        self._size = 0

    def items(self):
        """Recorre la lista nodo a nodo (de la cabeza al final)."""
        node = self.top
        while node is not None:
            yield node.getInfo()
            node = node.getNext()

    def printInfo(self):
        print("********* QUEUE DUMP *********")
        print("   Size: " + str(self._size))
        n = 1
        node = self.top
        while node is not None:
            print("   ** Element " + str(n))
            info = node.getInfo()
            if hasattr(info, "print"):
                info.print()
            else:
                print("     " + str(info))
            node = node.getNext()
            n += 1
        print("******************************")


# ----------------------------------------------------------------------------
# PRUEBA POR CONSOLA (equivale a TestQueue.java)
# ----------------------------------------------------------------------------
EXAMPLE_ORDERS = [(20, "Ana"), (30, "Luis"), (40, "Marta"), (50, "Pedro")]


def run_console_test():
    q = LinkedQueue()
    print(">>> Cola recién creada")
    q.printInfo()

    for qtty, cust in EXAMPLE_ORDERS:
        print(f">>> enqueue({cust}, {qtty})")
        q.enqueue(Order(qtty, cust))
        q.printInfo()

    print(">>> front() (no lo quita)")
    q.front().print()
    q.printInfo()

    print(">>> getTail() (el último, no lo quita)")
    q.getTail().print()

    print(">>> getNth(3)")
    q.getNth(3).print()

    print(">>> getNth con posiciones NO válidas: 0, -1, 5, 99, 'a'  ->",
          [q.getNth(p) for p in (0, -1, 5, 99, "a")])

    print(">>> dequeue()")
    q.dequeue().print()
    q.printInfo()

    print(">>> Vaciando la cola y probando dequeue/front con la cola vacía")
    while not q.isEmpty():
        q.dequeue()
    print("dequeue():", q.dequeue(), "| front():", q.front(), "| getNth(1):", q.getNth(1))
    q.printInfo()

    print(">>> Después de vaciarla, se puede volver a usar:")
    q.enqueue(Order(1, "Nuevo"))
    q.printInfo()


# ----------------------------------------------------------------------------
# INTERFAZ GRÁFICA (tkinter)
# ----------------------------------------------------------------------------
def run_gui():
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
        from tkinter import font as tkfont
    except ImportError:
        print("No se encontró tkinter. En Linux instálalo con:  sudo apt install python3-tk")
        sys.exit(1)

    # ---- paleta de colores ----
    BG = "#f3f4f8"
    CARD = "#ffffff"
    BORDER = "#e3e6ef"
    TEXT = "#1f2937"
    MUTED = "#6b7280"
    PRIMARY = "#4f46e5"
    PRIMARY_DARK = "#4338ca"
    GREEN = "#16a34a"
    ORANGE = "#ea580c"
    AMBER = "#f59e0b"
    RED = "#dc2626"

    STATUS_COLORS = {            # (fondo, texto, franja)
        "ok":    ("#ecfdf5", "#065f46", "#10b981"),
        "error": ("#fef2f2", "#991b1b", "#ef4444"),
        "info":  ("#eef2ff", "#3730a3", "#6366f1"),
    }

    def pick_font(root, candidates, fallback):
        available = set(tkfont.families(root))
        for name in candidates:
            if name in available:
                return name
        return fallback

    def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return canvas.create_polygon(pts, smooth=True, **kw)

    class App:
        def __init__(self, root):
            self.root = root
            self.queue = LinkedQueue()
            self.customer_var = tk.StringVar()
            self.qtty_var = tk.StringVar()
            self.pos_var = tk.StringVar()
            self.count_var = tk.StringVar()
            self.name_counter_var = tk.StringVar(value=f"0/{MAX_NAME_LEN}")

            self.ui = pick_font(root, ["Segoe UI", "SF Pro Text", "Helvetica Neue", "Noto Sans",
                                       "DejaVu Sans", "Helvetica"], "TkDefaultFont")
            self.mono = pick_font(root, ["Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono",
                                         "Courier New"], "Courier")
            self.setup_styles()
            self.build_ui()
            self.customer_var.trace_add("write", lambda *a: self.update_name_counter())
            self.refresh(log_title="Cola creada (vacía)")
            self.set_status("¡Bienvenido! Escribe un cliente y una cantidad y pulsa «Añadir a la cola».", "info")
            self.customer_entry.focus_set()

        # ---------------- estilos ----------------
        def setup_styles(self):
            ui = self.ui
            self.root.configure(bg=BG)
            st = ttk.Style(self.root)
            try:
                st.theme_use("clam")
            except tk.TclError:
                pass
            st.configure(".", font=(ui, 10), background=BG)

            # cajas de texto
            st.configure("Field.TEntry", fieldbackground="#ffffff", foreground=TEXT, padding=7,
                         bordercolor="#cfd5e3", lightcolor="#cfd5e3", darkcolor="#cfd5e3",
                         insertcolor=TEXT)
            st.map("Field.TEntry", bordercolor=[("focus", PRIMARY)],
                   lightcolor=[("focus", PRIMARY)], darkcolor=[("focus", PRIMARY)])
            st.configure("Bad.TEntry", fieldbackground="#fee2e2", foreground=TEXT, padding=7,
                         bordercolor=RED, lightcolor=RED, darkcolor=RED, insertcolor=TEXT)

            # botones
            def button(name, bg, hover, fg):
                st.configure(name, background=bg, foreground=fg, bordercolor=bg, lightcolor=bg,
                             darkcolor=bg, focuscolor=bg, borderwidth=1, relief="flat",
                             padding=(14, 8), font=(ui, 10, "bold"))
                both = [("active", hover), ("pressed", hover)]
                st.map(name, background=both, bordercolor=both, lightcolor=both, darkcolor=both)

            button("Primary.TButton", PRIMARY, PRIMARY_DARK, "#ffffff")
            button("Success.TButton", GREEN, "#15803d", "#ffffff")
            button("Neutral.TButton", "#eceff6", "#dde2ee", TEXT)
            button("Danger.TButton", "#fee2e2", "#fecaca", "#b91c1c")

            # tabla
            st.configure("Pedidos.Treeview", background="#ffffff", fieldbackground="#ffffff",
                         foreground=TEXT, rowheight=30, borderwidth=0, font=(ui, 10))
            st.configure("Pedidos.Treeview.Heading", background="#eef0f6", foreground=TEXT,
                         font=(ui, 10, "bold"), padding=7, relief="flat")
            st.map("Pedidos.Treeview", background=[("selected", PRIMARY)],
                   foreground=[("selected", "#ffffff")])
            st.map("Pedidos.Treeview.Heading", background=[("active", "#e0e4ef")])

        # ---------------- construcción de la ventana ----------------
        def card(self, parent, title):
            """Tarjeta blanca con borde suave. Devuelve (marco_exterior, cuerpo)."""
            outer = tk.Frame(parent, bg=BORDER)
            inner = tk.Frame(outer, bg=CARD, padx=16, pady=12)
            inner.pack(fill="both", expand=True, padx=1, pady=1)
            if title:
                tk.Label(inner, text=title, bg=CARD, fg=TEXT, font=(self.ui, 11, "bold")).pack(anchor="w")
            body = tk.Frame(inner, bg=CARD)
            body.pack(fill="both", expand=True, pady=(8, 0))
            return outer, body

        def build_ui(self):
            root, ui = self.root, self.ui
            root.title("Cola de pedidos (FIFO) – lista enlazada")

            # tamaño de la ventana adaptado a la pantalla (nunca más grande que ella)
            sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
            w, h = min(1220, sw - 40), min(800, sh - 100)
            root.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 20)}")
            root.minsize(min(1080, w), min(640, h))

            # cabecera
            header = tk.Frame(root, bg=PRIMARY, padx=24, pady=10)
            header.pack(fill="x")
            tk.Label(header, text="Cola de pedidos", bg=PRIMARY, fg="#ffffff",
                     font=(ui, 18, "bold")).pack(anchor="w")
            tk.Label(header, bg=PRIMARY, fg="#c7d2fe", font=(ui, 9),
                     text="FIFO (First In, First Out): el primero en llegar es el primero en ser atendido. "
                          "Los pedidos entran por el FINAL y salen por el FRENTE.").pack(anchor="w")

            # dos columnas: izquierda = controles + dibujo, derecha = tabla + registro
            main = tk.Frame(root, bg=BG, padx=20, pady=12)
            main.pack(fill="both", expand=True)
            main.columnconfigure(0, weight=3)
            main.columnconfigure(1, weight=2, minsize=380)
            main.rowconfigure(0, weight=1)
            left = tk.Frame(main, bg=BG)
            left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
            right = tk.Frame(main, bg=BG)
            right.grid(row=0, column=1, sticky="nsew")
            right.columnconfigure(0, weight=1)
            right.rowconfigure(0, weight=1, uniform="r")
            right.rowconfigure(1, weight=1, uniform="r")

            reg = root.register

            # ---- tarjeta: nuevo pedido ----
            add_outer, add = self.card(left, "Nuevo pedido")
            add_outer.pack(fill="x")
            add.columnconfigure(0, weight=3)
            add.columnconfigure(1, weight=2)

            f1 = tk.Frame(add, bg=CARD)
            f1.grid(row=0, column=0, sticky="ew", padx=(0, 14))
            row1 = tk.Frame(f1, bg=CARD)
            row1.pack(fill="x")
            tk.Label(row1, text="Cliente", bg=CARD, fg=TEXT, font=(ui, 10, "bold")).pack(side="left")
            self.name_counter = tk.Label(row1, textvariable=self.name_counter_var, bg=CARD, fg=MUTED,
                                         font=(ui, 10, "bold"))
            self.name_counter.pack(side="right")
            self.customer_entry = ttk.Entry(
                f1, textvariable=self.customer_var, style="Field.TEntry", font=(ui, 11),
                validate="key", validatecommand=(reg(self.validate_name), "%P"))
            self.customer_entry.pack(fill="x", pady=(4, 3))
            tk.Label(f1, text=f"Solo letras (con tildes y ñ) · máximo {MAX_NAME_LEN} caracteres",
                     bg=CARD, fg=MUTED, font=(ui, 9)).pack(anchor="w")

            f2 = tk.Frame(add, bg=CARD)
            f2.grid(row=0, column=1, sticky="ew", padx=(0, 14))
            row2 = tk.Frame(f2, bg=CARD)
            row2.pack(fill="x")
            tk.Label(row2, text="Cantidad", bg=CARD, fg=TEXT, font=(ui, 10, "bold")).pack(side="left")
            tk.Label(row2, text=f"máx. {fmt_num(MAX_QTTY)}", bg=CARD, fg=MUTED,
                     font=(ui, 10, "bold")).pack(side="right")
            self.qtty_entry = ttk.Entry(
                f2, textvariable=self.qtty_var, style="Field.TEntry", font=(ui, 11),
                validate="key", validatecommand=(reg(self.validate_qtty), "%P"))
            self.qtty_entry.pack(fill="x", pady=(4, 3))
            tk.Label(f2, text=f"Solo números enteros · de 1 a {fmt_num(MAX_QTTY)}",
                     bg=CARD, fg=MUTED, font=(ui, 9)).pack(anchor="w")

            ttk.Button(add, text="Añadir a la cola", style="Primary.TButton", cursor="hand2",
                       command=self.add_order).grid(row=0, column=2, sticky="n", pady=(21, 0))

            self.customer_entry.bind("<Return>", lambda e: self.qtty_entry.focus_set())
            self.qtty_entry.bind("<Return>", lambda e: self.add_order())

            # ---- tarjeta: acciones ----
            act_outer, act = self.card(left, "Acciones")
            act_outer.pack(fill="x", pady=10)
            for col in range(3):
                act.columnconfigure(col, weight=1, uniform="a")

            ttk.Button(act, text="Atender (dequeue)", style="Success.TButton", cursor="hand2",
                       command=self.dequeue).grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=(0, 8))
            ttk.Button(act, text="Ver primero (front)", style="Neutral.TButton", cursor="hand2",
                       command=self.front).grid(row=0, column=1, sticky="ew", padx=5, pady=(0, 8))
            ttk.Button(act, text="Ver último (tail)", style="Neutral.TButton", cursor="hand2",
                       command=self.show_tail).grid(row=0, column=2, sticky="ew", padx=(5, 0), pady=(0, 8))

            row_b = tk.Frame(act, bg=CARD)
            row_b.grid(row=1, column=0, columnspan=3, sticky="ew")
            # primero los de la derecha, para que el botón del medio se estire y ocupe todo el hueco
            ttk.Button(row_b, text="Vaciar cola", style="Danger.TButton", cursor="hand2",
                       command=self.clear_queue).pack(side="right")
            ttk.Button(row_b, text="Cargar ejemplo", style="Neutral.TButton", cursor="hand2",
                       command=self.load_example).pack(side="right", padx=(0, 8))
            tk.Label(row_b, text="Posición", bg=CARD, fg=TEXT, font=(ui, 10, "bold")).pack(side="left", padx=(0, 6))
            self.pos_entry = ttk.Entry(row_b, textvariable=self.pos_var, style="Field.TEntry", width=4,
                                       font=(ui, 11), validate="key",
                                       validatecommand=(reg(self.validate_pos), "%P"))
            self.pos_entry.pack(side="left", padx=(0, 8))
            ttk.Button(row_b, text="Ver ese pedido (getNth)", style="Neutral.TButton",
                       cursor="hand2", command=self.get_nth).pack(side="left", fill="x", expand=True,
                                                                  padx=(0, 8))
            self.pos_entry.bind("<Return>", lambda e: self.get_nth())

            # ---- mensajes ----
            self.status_wrap = tk.Frame(left, bg=STATUS_COLORS["info"][0])
            self.status_wrap.pack(fill="x", pady=(0, 10))
            self.status_stripe = tk.Frame(self.status_wrap, width=6, bg=STATUS_COLORS["info"][2])
            self.status_stripe.pack(side="left", fill="y")
            self.status = tk.Label(self.status_wrap, text="", anchor="w", justify="left",
                                   padx=14, pady=10, font=(ui, 11))
            self.status.pack(side="left", fill="x", expand=True)
            self.status_wrap.bind("<Configure>", lambda e: self.status.configure(wraplength=max(250, e.width - 60)))

            # ---- tarjeta: dibujo de la cola ----
            q_outer, q_body = self.card(left, None)
            q_outer.pack(fill="both", expand=True)
            top_row = tk.Frame(q_body, bg=CARD)
            top_row.pack(fill="x")
            tk.Label(top_row, text="Así está la cola ahora", bg=CARD, fg=TEXT,
                     font=(ui, 11, "bold")).pack(side="left")
            self.count_pill = tk.Label(top_row, textvariable=self.count_var, bg="#eef2ff", fg=PRIMARY_DARK,
                                       font=(ui, 10, "bold"), padx=12, pady=3)
            self.count_pill.pack(side="right")
            cframe = tk.Frame(q_body, bg=CARD)
            cframe.pack(fill="x", pady=(8, 0))
            self.canvas = tk.Canvas(cframe, height=150, bg="#f8f9fd", highlightthickness=1,
                                    highlightbackground=BORDER)
            hbar = ttk.Scrollbar(cframe, orient="horizontal", command=self.canvas.xview)
            self.canvas.configure(xscrollcommand=hbar.set)
            self.canvas.pack(fill="x")
            hbar.pack(fill="x")

            # ---- columna derecha: tabla (arriba) y registro (abajo), con toda la altura ----
            t_outer, t_body = self.card(right, "Lista de pedidos")
            t_outer.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
            cols = ("pos", "cliente", "cantidad")
            self.tree = ttk.Treeview(t_body, columns=cols, show="headings", height=5,
                                     selectmode="browse", style="Pedidos.Treeview")
            self.tree.heading("pos", text="Pos.")
            self.tree.heading("cliente", text="Cliente")
            self.tree.heading("cantidad", text="Cantidad")
            self.tree.column("pos", width=55, anchor="center", stretch=False)
            self.tree.column("cliente", width=150, anchor="w", stretch=True)
            self.tree.column("cantidad", width=110, anchor="e", stretch=False)
            self.tree.tag_configure("odd", background="#f8f9fc")
            vs = ttk.Scrollbar(t_body, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=vs.set)
            self.tree.pack(side="left", fill="both", expand=True)
            vs.pack(side="right", fill="y")

            l_outer, l_body = self.card(right, "Registro (lo mismo que sale por consola)")
            l_outer.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
            self.log = tk.Text(l_body, height=5, width=10, state="disabled", wrap="none",
                               font=(self.mono, 9), bg="#0f172a", fg="#e2e8f0", bd=0,
                               padx=10, pady=8, insertbackground="#e2e8f0")
            self.log.tag_configure("title", foreground="#38bdf8", font=(self.mono, 9, "bold"))
            ls = ttk.Scrollbar(l_body, orient="vertical", command=self.log.yview)
            self.log.configure(yscrollcommand=ls.set)
            self.log.pack(side="left", fill="both", expand=True)
            ls.pack(side="right", fill="y")

        # ---------------- validación mientras se escribe ----------------
        def reject(self, entry, message):
            """Bloquea la tecla, avisa con un mensaje y pone la caja roja un momento."""
            self.set_status(message, "error")
            entry.configure(style="Bad.TEntry")
            self.root.after(350, lambda: entry.configure(style="Field.TEntry"))

        def validate_name(self, new_text):
            error = name_typing_error(new_text)
            if error:
                self.reject(self.customer_entry, error)
                return False
            return True

        def validate_qtty(self, new_text):
            error = qtty_typing_error(new_text)
            if error:
                self.reject(self.qtty_entry, error)
                return False
            return True

        def validate_pos(self, new_text):
            error = pos_typing_error(new_text)
            if error:
                self.reject(self.pos_entry, error)
                return False
            return True

        def update_name_counter(self):
            n = len(self.customer_var.get())
            self.name_counter_var.set(f"{n}/{MAX_NAME_LEN}")
            self.name_counter.configure(fg="#b45309" if n >= MAX_NAME_LEN else MUTED)

        # ---------------- utilidades ----------------
        def set_status(self, msg, kind="info"):
            bg, fg, stripe = STATUS_COLORS[kind]
            self.status_wrap.configure(bg=bg)
            self.status_stripe.configure(bg=stripe)
            self.status.configure(text=msg, bg=bg, fg=fg)

        @staticmethod
        def describe(order):
            return f"{order.getCustomer()} (cantidad: {fmt_num(order.getQtty())})"

        def dump_text(self):
            """Ejecuta printInfo() de la cola: sale por consola y también se guarda para el registro."""
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.queue.printInfo()
            text = buf.getvalue()
            if sys.stdout is not None:
                try:
                    sys.stdout.write(text)
                    sys.stdout.flush()
                except Exception:
                    pass
            return text

        def write_log(self, title, dump):
            self.log.configure(state="normal")
            self.log.insert("end", f"> {title}\n", "title")
            self.log.insert("end", dump + "\n")
            if int(self.log.index("end-1c").split(".")[0]) > 1500:   # no dejar crecer el registro sin límite
                self.log.delete("1.0", "500.0")
            self.log.see("end")
            self.log.configure(state="disabled")

        def refresh(self, highlight=None, log_title=None):
            """Redibuja todo. highlight = posición (desde 1) a resaltar."""
            items = list(self.queue.items())
            n = len(items)
            self.count_var.set(f"{n} pedido{'s' if n != 1 else ''} en la cola" if n else "Cola vacía")

            # tabla
            self.tree.delete(*self.tree.get_children())
            for i, o in enumerate(items, 1):
                self.tree.insert("", "end", iid=str(i), tags=("odd",) if i % 2 == 0 else (),
                                 values=(i, o.getCustomer(), fmt_num(o.getQtty())))
            if highlight and 1 <= highlight <= n:
                self.tree.selection_set(str(highlight))
                self.tree.see(str(highlight))

            self.draw_queue(items, highlight)

            if log_title is not None:
                self.write_log(log_title, self.dump_text())

        def draw_queue(self, items, highlight):
            c, ui = self.canvas, self.ui
            c.delete("all")
            if not items:
                c.create_text(24, 55, anchor="w", fill=TEXT, font=(ui, 13, "bold"),
                              text="La cola está vacía")
                c.create_text(24, 83, anchor="w", fill=MUTED, font=(ui, 10),
                              text="Añade un pedido arriba para empezar a ver cómo se enlazan los nodos.")
                c.configure(scrollregion=(0, 0, 10, 150))
                c.xview_moveto(0)
                return

            x, y, w, h, gap = 20, 46, 160, 80, 52
            last = len(items) - 1
            for i, o in enumerate(items):
                is_hl = (highlight == i + 1)
                accent = GREEN if i == 0 else (ORANGE if i == last else PRIMARY)

                # sombra + tarjeta
                rounded_rect(c, x + 3, y + 4, x + w + 3, y + h + 4, 12, fill="#e0e4ef", outline="")
                rounded_rect(c, x, y, x + w, y + h, 12,
                             fill="#fef3c7" if is_hl else "#ffffff",
                             outline=AMBER if is_hl else "#d5dae8", width=3 if is_hl else 1)

                # círculo con el número
                c.create_oval(x + 12, y + 12, x + 38, y + 38, fill=accent, outline="")
                c.create_text(x + 25, y + 25, text=str(i + 1), fill="#ffffff", font=(ui, 10, "bold"))

                name = o.getCustomer()
                if len(name) > 13:
                    name = name[:12] + "…"
                c.create_text(x + 46, y + 25, anchor="w", text=name, fill=TEXT, font=(ui, 11, "bold"))
                c.create_line(x + 14, y + 46, x + w - 14, y + 46, fill="#e5e7eb")
                c.create_text(x + 14, y + 63, anchor="w", text="Cantidad", fill=MUTED, font=(ui, 9))
                c.create_text(x + w - 14, y + 63, anchor="e", text=fmt_num(o.getQtty()), fill=TEXT,
                              font=(ui, 11, "bold"))

                # etiqueta FRENTE / FINAL
                label = None
                if i == 0 and i == last:
                    label, bg, fg = "FRENTE y FINAL", "#e0e7ff", PRIMARY_DARK
                elif i == 0:
                    label, bg, fg = "FRENTE (top)", "#dcfce7", "#166534"
                elif i == last:
                    label, bg, fg = "FINAL (tail)", "#ffedd5", "#9a3412"
                if label:
                    t = c.create_text(x + w / 2, y - 20, text=label, fill=fg, font=(ui, 9, "bold"))
                    x1, y1, x2, y2 = c.bbox(t)
                    pill = rounded_rect(c, x1 - 10, y1 - 3, x2 + 10, y2 + 3, 9, fill=bg, outline="")
                    c.tag_lower(pill, t)

                # flecha al siguiente nodo (o null)
                my = y + h / 2
                if i < last:
                    c.create_line(x + w + 6, my, x + w + gap - 6, my, arrow=tk.LAST, width=2,
                                  fill="#9ca3af", arrowshape=(10, 12, 4))
                    c.create_text(x + w + gap / 2, my - 12, text="next", fill=MUTED, font=(ui, 8))
                else:
                    c.create_line(x + w + 6, my, x + w + 30, my, arrow=tk.LAST, width=2,
                                  fill="#d1d5db", arrowshape=(10, 12, 4))
                    c.create_text(x + w + 36, my, anchor="w", text="null", fill=MUTED,
                                  font=(ui, 10, "italic"))
                x += w + gap

            total = x + 40
            c.configure(scrollregion=(0, 0, total, 150))
            if highlight:   # mover el scroll para que se vea el pedido resaltado
                c.xview_moveto(max(0.0, ((highlight - 1) * (w + gap) - 150) / total))
            else:
                c.xview_moveto(0)

        # ---------------- acciones ----------------
        def add_order(self):
            try:
                name = clean_customer(self.customer_var.get())
            except ValueError as e:
                self.set_status(str(e), "error")
                self.customer_entry.focus_set()
                return
            try:
                qtty = parse_positive_int(self.qtty_var.get(), "la cantidad", MAX_QTTY)
            except ValueError as e:
                self.set_status(str(e), "error")
                self.qtty_entry.focus_set()
                self.qtty_entry.selection_range(0, "end")
                return
            try:
                self.queue.enqueue(Order(qtty, name))
            except (OverflowError, ValueError) as e:
                self.set_status(str(e), "error")
                return
            self.customer_var.set("")
            self.qtty_var.set("")
            self.customer_entry.focus_set()
            self.refresh(highlight=self.queue.size(), log_title=f"enqueue -> {name}, {qtty}")
            self.set_status(f"Pedido añadido: {name} (cantidad: {fmt_num(qtty)}). "
                            f"Está en la posición {self.queue.size()}.", "ok")

        def dequeue(self):
            order = self.queue.dequeue()
            if order is None:
                self.refresh(log_title="dequeue -> null (cola vacía)")
                self.set_status("La cola está vacía: no hay ningún pedido que atender.", "info")
                return
            self.refresh(log_title=f"dequeue -> {order.getCustomer()}, {order.getQtty()}")
            left = self.queue.size()
            self.set_status(f"Pedido atendido y sacado de la cola: {self.describe(order)}. "
                            f"Quedan {left} pedido{'s' if left != 1 else ''}.", "ok")

        def front(self):
            order = self.queue.front()
            if order is None:
                self.refresh(log_title="front -> null (cola vacía)")
                self.set_status("La cola está vacía: no hay primer pedido.", "info")
                return
            self.refresh(highlight=1, log_title=f"front -> {order.getCustomer()}, {order.getQtty()}")
            self.set_status(f"El primero de la cola es: {self.describe(order)} "
                            f"(no se ha quitado de la cola).", "info")

        def show_tail(self):
            order = self.queue.getTail()
            if order is None:
                self.refresh(log_title="getTail -> null (cola vacía)")
                self.set_status("La cola está vacía: no hay último pedido.", "info")
                return
            self.refresh(highlight=self.queue.size(),
                         log_title=f"getTail -> {order.getCustomer()}, {order.getQtty()}")
            self.set_status(f"El último de la cola es: {self.describe(order)} "
                            f"(no se ha quitado de la cola).", "info")

        def get_nth(self):
            try:
                pos = parse_positive_int(self.pos_var.get(), "la posición", 10 ** 9)
            except ValueError as e:
                self.set_status(str(e) + " (las posiciones empiezan en 1)", "error")
                self.pos_entry.focus_set()
                self.pos_entry.selection_range(0, "end")
                return
            order = self.queue.getNth(pos)
            if order is None:
                n = self.queue.size()
                self.refresh(log_title=f"getNth({pos}) -> null (posición no válida)")
                if n == 0:
                    self.set_status(f"Posición {pos} no válida: la cola está vacía.", "error")
                else:
                    self.set_status(f"Posición {pos} no válida: la cola solo tiene {n} "
                                    f"pedido{'s' if n != 1 else ''} (elige de 1 a {n}).", "error")
                return
            self.refresh(highlight=pos, log_title=f"getNth({pos}) -> {order.getCustomer()}, {order.getQtty()}")
            self.set_status(f"El pedido en la posición {pos} es: {self.describe(order)} "
                            f"(no se ha quitado de la cola).", "info")

        def load_example(self):
            if self.queue.size() + len(EXAMPLE_ORDERS) > MAX_QUEUE_SIZE:
                self.set_status(f"No caben {len(EXAMPLE_ORDERS)} pedidos más en la cola.", "error")
                return
            for qtty, cust in EXAMPLE_ORDERS:
                self.queue.enqueue(Order(qtty, cust))
            self.refresh(log_title=f"Ejemplo cargado: {len(EXAMPLE_ORDERS)} pedidos")
            self.set_status(f"Se añadieron {len(EXAMPLE_ORDERS)} pedidos de ejemplo. Prueba a escribir 3 en "
                            f"«Posición» y pulsar «Ver ese pedido».", "ok")

        def clear_queue(self):
            if self.queue.isEmpty():
                self.set_status("La cola ya está vacía.", "info")
                return
            if messagebox.askyesno("Vaciar cola", f"¿Seguro que quieres borrar los "
                                                  f"{self.queue.size()} pedidos de la cola?"):
                self.queue.clear()
                self.refresh(log_title="Cola vaciada")
                self.set_status("Cola vaciada.", "ok")

    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_console_test()
    else:
        run_gui()