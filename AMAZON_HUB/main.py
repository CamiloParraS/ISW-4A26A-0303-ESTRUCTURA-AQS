"""
=============================================================
  LOGISTICS AND DELIVERY ROUTE SIMULATOR — Amazon Hub
=============================================================
  Data Structures Used:
    - Queue  (collections.deque) → Customer Order Reception (FIFO)
    - Stack  (Python list)       → Truck Loading Management (LIFO)
    - Array  (Python list)       → Fixed Warehouse Shelving Inventory
=============================================================
  Requirements: PyQt6
  Install:  pip install PyQt6
  Run:      python amazon_hub_simulator.py
=============================================================
"""

import sys
import bisect
from collections import deque
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QFrame, QMessageBox, QGridLayout, QGroupBox, QGraphicsOpacityEffect,
    QComboBox, QScrollArea, QSpinBox, QAbstractItemView,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QColor, QPalette, QLinearGradient, QPainter, QBrush, QPen


# Colour tokens — used for QColor() and log highlighting (not CSS)
ACCENT   = "#FF9900"
BLUE     = "#4A9EFF"
GREEN    = "#3DCA7A"
RED      = "#FF4D4D"
TEXT_DIM = "#7A8499"
BG_CARD  = "#1E2330"


# ==============================================================
#  CATEGORIES  (Shelf positions are INDEX-based → Array concept)
# ==============================================================
CATEGORIES = ["Electronics", "Clothing", "Food", "Books", "Toys", "Appliances"]
CATEGORY_ICONS = {
    "Electronics": "⚡",
    "Clothing":    "",
    "Food":        "",
    "Books":       "",
    "Toys":        "",
    "Appliances":  "",
}

DESTINATIONS = ["Downtown", "North Zone", "South Zone", "Airport", "Mall", "Port"]


# ==============================================================
#  HELPER — Create a styled separator line
# ==============================================================
def make_separator():
    line = QFrame()
    line.setObjectName("separator")
    line.setFrameShape(QFrame.Shape.HLine)
    return line


# ==============================================================
#  HELPER — Section header with badge
# ==============================================================
def make_section_header(title, subtitle, badge_text):
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    top_row = QHBoxLayout()
    top_row.setSpacing(8)

    title_lbl = QLabel(title)
    title_lbl.setObjectName("section_title")

    badge_lbl = QLabel(badge_text)
    badge_lbl.setObjectName("badge")

    top_row.addWidget(title_lbl)
    top_row.addWidget(badge_lbl)
    top_row.addStretch()

    sub_lbl = QLabel(subtitle)
    sub_lbl.setObjectName("section_subtitle")

    layout.addLayout(top_row)
    layout.addWidget(sub_lbl)

    return container


# ==============================================================
#  DATA STRUCTURES
# ==============================================================

class OrderQueue:
    """
    FIFO Queue using collections.deque.
    Represents the Customer Order Reception desk.
    Orders are processed in the order they arrive (first come, first served).
    """

    def __init__(self):
        self.queue = deque()  # <-- QUEUE (FIFO)
        self.order_counter = 1

    def enqueue(self, package_name, category):
        order_id = f"ORD-{self.order_counter:04d}"
        self.order_counter += 1
        order = {
            "id":       order_id,
            "name":     package_name,
            "category": category,
        }
        self.queue.append(order)   # Add to the BACK of the queue
        return order

    def dequeue(self):
        if len(self.queue) == 0:
            return None
        return self.queue.popleft()   # Remove from the FRONT (FIFO)

    def size(self):
        return len(self.queue)

    def is_empty(self):
        return len(self.queue) == 0

    def peek(self):
        if self.queue:
            return self.queue[0]
        return None

    def all_items(self):
        return list(self.queue)


class WarehouseInventory:
    """
    ARRAY representing fixed physical shelf positions in the warehouse.
    Each index corresponds to a category aisle:
      Index 0 → Electronics Aisle A1
      Index 1 → Clothing Aisle B2
      ... etc.
    Each slot holds a list of packages stored there.
    """

    def __init__(self):
        # ARRAY with fixed size — one slot per category
        self.shelves = [[] for _ in CATEGORIES]  # <-- ARRAY (fixed positions)

    def get_aisle_index(self, category):
        return CATEGORIES.index(category)

    def store_package(self, package):
        idx = self.get_aisle_index(package["category"])
        self.shelves[idx].append(package)

    def get_packages_in_aisle(self, category):
        idx = self.get_aisle_index(category)
        return list(self.shelves[idx])

    def remove_package_from_aisle(self, category):
        idx = self.get_aisle_index(category)
        if len(self.shelves[idx]) > 0:
            return self.shelves[idx].pop(0)
        return None

    def count_in_aisle(self, category):
        idx = self.get_aisle_index(category)
        return len(self.shelves[idx])

    def total_packages(self):
        total = 0
        for slot in self.shelves:
            total += len(slot)
        return total

    def check_shelf(self, category):
        idx = self.get_aisle_index(category)
        packages = self.shelves[idx]
        return idx, packages


class TruckStack:
    """
    LIFO Stack using a Python list.
    Represents the truck loading bay.
    The LAST package loaded is the FIRST one delivered (top of stack).

    Optimization: When loading for a specific destination, we only
    load packages heading there — so at each stop the driver grabs
    packages from the top without re-organizing the whole truck.
    """

    def __init__(self):
        self.stack = []   # <-- STACK (LIFO)
        self.max_capacity = 20

    def push(self, package):
        if len(self.stack) >= self.max_capacity:
            return False, "Truck is full! (max 20 packages)"
        self.stack.append(package)   # Push on TOP
        return True, "OK"

    def pop(self):
        if len(self.stack) == 0:
            return None
        return self.stack.pop()   # Pop from TOP (LIFO)

    def peek(self):
        if self.stack:
            return self.stack[-1]
        return None

    def size(self):
        return len(self.stack)

    def is_empty(self):
        return len(self.stack) == 0

    def is_full(self):
        return len(self.stack) >= self.max_capacity

    def all_items(self):
        # Return with top-of-stack first (reversed for display)
        return list(reversed(self.stack))


# ==============================================================
#  MAIN WINDOW
# ==============================================================

class AmazonHubSimulator(QMainWindow):

    def __init__(self):
        super().__init__()

        # ── Instantiate the data structures ──
        self.order_queue  = OrderQueue()
        self.warehouse    = WarehouseInventory()
        self.truck        = TruckStack()
        self.event_log    = []   # Activity log list

        self.setWindowTitle("Amazon Hub — Logistics & Delivery Route Simulator")
        self.setMinimumSize(1400, 820)
        self.resize(1440, 860)


        self._build_ui()
        self._refresh_all()

        # Load some demo data so the UI isn't empty on launch
        self._load_demo_data()

    # ----------------------------------------------------------
    #  BUILD UI
    # ----------------------------------------------------------
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # ── TOP HEADER BAR ──
        main_layout.addWidget(self._build_header())
        main_layout.addWidget(make_separator())

        # ── THREE COLUMN LAYOUT ──
        columns = QHBoxLayout()
        columns.setSpacing(12)
        columns.addWidget(self._build_queue_panel(),      stretch=30)
        columns.addWidget(self._build_inventory_panel(),  stretch=35)
        columns.addWidget(self._build_truck_panel(),      stretch=35)
        main_layout.addLayout(columns, stretch=1)

        # ── ACTIVITY LOG ──
        main_layout.addWidget(make_separator())
        main_layout.addWidget(self._build_log_bar())

    # ----------------------------------------------------------
    #  HEADER
    # ----------------------------------------------------------
    def _build_header(self):
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 2, 4, 2)

        logo_lbl = QLabel("  AMAZON HUB")

        subtitle = QLabel("Logistics & Delivery Route Simulator")

        layout.addWidget(logo_lbl)
        layout.addWidget(subtitle)
        layout.addStretch()

        # Stats row
        self.stat_orders = self._make_stat_widget("ORDERS RECEIVED", "0")
        self.stat_stored  = self._make_stat_widget("IN WAREHOUSE",   "0")
        self.stat_truck   = self._make_stat_widget("ON TRUCK",       "0")

        for w in [self.stat_orders, self.stat_stored, self.stat_truck]:
            layout.addWidget(w)
            layout.addWidget(self._make_v_separator())

        return bar

    def _make_stat_widget(self, label, value):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 0, 12, 0)
        v.setSpacing(1)

        lbl = QLabel(label)
        lbl.setObjectName("stat_label")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        val = QLabel(value)
        val.setObjectName("stat_value")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        v.addWidget(lbl)
        v.addWidget(val)

        # Store ref on the value label
        w._val_label = val
        return w

    def _make_v_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        return line

    # ----------------------------------------------------------
    #  COLUMN 1 — QUEUE (Customer Order Reception)
    # ----------------------------------------------------------
    def _build_queue_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header
        layout.addWidget(make_section_header(
            "ORDER RECEPTION",
            "FIFO Queue  —  First In, First Out",
            "QUEUE"
        ))
        layout.addWidget(make_separator())

        # ── Input form ──
        form = QGridLayout()
        form.setSpacing(6)

        form.addWidget(self._lbl("Package Name:"), 0, 0)
        self.input_pkg_name = QLineEdit()
        self.input_pkg_name.setPlaceholderText("e.g. Laptop Pro 15, T-Shirt Blue...")
        form.addWidget(self.input_pkg_name, 0, 1)

        form.addWidget(self._lbl("Category:"), 1, 0)
        self.combo_category = QComboBox()
        for cat in CATEGORIES:
            icon = CATEGORY_ICONS[cat]
            self.combo_category.addItem(f"{icon}  {cat}")
        form.addWidget(self.combo_category, 1, 1)

        layout.addLayout(form)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_receive = QPushButton("  Receive Order")
        btn_receive.setObjectName("btn_primary")
        btn_receive.clicked.connect(self._receive_order)

        btn_clear = QPushButton("  Clear Queue")
        btn_clear.setObjectName("btn_danger")
        btn_clear.clicked.connect(self._clear_queue)

        btn_row.addWidget(btn_receive, stretch=2)
        btn_row.addWidget(btn_clear, stretch=1)
        layout.addLayout(btn_row)

        layout.addWidget(make_separator())

        # ── Queue info ──
        info_row = QHBoxLayout()
        info_row.addWidget(self._lbl("Next to process:"))
        self.lbl_queue_front = QLabel("—")
        info_row.addWidget(self.lbl_queue_front)
        info_row.addStretch()
        layout.addLayout(info_row)

        # ── Queue list ──
        q_header_row = QHBoxLayout()
        q_header_row.addWidget(self._lbl("Queue Contents  (top = next)"))
        self.lbl_queue_count = QLabel("0 orders")
        q_header_row.addStretch()
        q_header_row.addWidget(self.lbl_queue_count)
        layout.addLayout(q_header_row)

        self.list_queue = QListWidget()
        self.list_queue.setMinimumHeight(220)
        layout.addWidget(self.list_queue, stretch=1)

        # ── Move to inventory button ──
        btn_to_inv = QPushButton("  Move Front Order → Warehouse")
        btn_to_inv.setObjectName("btn_success")
        btn_to_inv.clicked.connect(self._move_queue_to_inventory)
        layout.addWidget(btn_to_inv)

        return panel

    # ----------------------------------------------------------
    #  COLUMN 2 — ARRAY (Warehouse Shelving Inventory)
    # ----------------------------------------------------------
    def _build_inventory_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header
        layout.addWidget(make_section_header(
            "WAREHOUSE INVENTORY",
            "Fixed Array  —  Indexed by Category Aisle",
            "ARRAY"
        ))
        layout.addWidget(make_separator())

        shelf_row = QHBoxLayout()
        shelf_row.addWidget(self._lbl("Check Shelf:"))
        self.combo_check_shelf = QComboBox()
        for cat in CATEGORIES:
            icon = CATEGORY_ICONS[cat]
            self.combo_check_shelf.addItem(f"{icon}  {cat}")
        shelf_row.addWidget(self.combo_check_shelf, stretch=1)

        btn_check = QPushButton("  Check Shelf")
        btn_check.setObjectName("btn_info")
        btn_check.clicked.connect(self._check_shelf)
        shelf_row.addWidget(btn_check)
        layout.addLayout(shelf_row)

        self.lbl_shelf_result = QLabel("")
        self.lbl_shelf_result.setWordWrap(True)
        layout.addWidget(self.lbl_shelf_result)

        layout.addWidget(make_separator())

        # ── Shelf grid (all 6 aisles) ──
        layout.addWidget(self._lbl("Aisle Overview  (all positions):"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        shelf_container = QWidget()
        shelf_grid = QGridLayout(shelf_container)
        shelf_grid.setSpacing(8)
        shelf_grid.setContentsMargins(0, 4, 0, 4)

        self.shelf_widgets = {}   

        for i, cat in enumerate(CATEGORIES):
            icon = CATEGORY_ICONS[cat]
            row_frame = QFrame()
            row_frame.setObjectName("panel")
            row_v = QVBoxLayout(row_frame)
            row_v.setContentsMargins(8, 6, 8, 6)
            row_v.setSpacing(4)

            title_row = QHBoxLayout()
            aisle_lbl = QLabel(f"[{i}]  {icon} {cat}")
            count_lbl = QLabel("0 pkgs")

            title_row.addWidget(aisle_lbl)
            title_row.addStretch()
            title_row.addWidget(count_lbl)
            row_v.addLayout(title_row)

            pkg_list = QListWidget()
            pkg_list.setMaximumHeight(70)
            row_v.addWidget(pkg_list)

            shelf_grid.addWidget(row_frame, i, 0)
            self.shelf_widgets[cat] = (count_lbl, pkg_list)

        scroll.setWidget(shelf_container)
        layout.addWidget(scroll, stretch=1)

        # ── Load to Truck button ──
        load_row = QHBoxLayout()

        load_row.addWidget(self._lbl("Destination:"))
        self.combo_destination = QComboBox()
        for dest in DESTINATIONS:
            self.combo_destination.addItem(f"  {dest}")
        load_row.addWidget(self.combo_destination, stretch=1)

        load_row.addWidget(self._lbl("Qty:"))
        self.spin_load_qty = QSpinBox()
        self.spin_load_qty.setMinimum(1)
        self.spin_load_qty.setMaximum(20)
        self.spin_load_qty.setValue(3)
        self.spin_load_qty.setFixedWidth(60)
        load_row.addWidget(self.spin_load_qty)

        layout.addLayout(load_row)

        btn_load = QPushButton("  Load Truck  (Queue → Truck Stack)")
        btn_load.setObjectName("btn_primary")
        btn_load.clicked.connect(self._load_truck)
        layout.addWidget(btn_load)

        return panel

    # ----------------------------------------------------------
    #  COLUMN 3 — STACK (Truck Loading)
    # ----------------------------------------------------------
    def _build_truck_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header
        layout.addWidget(make_section_header(
            "TRUCK LOADING BAY",
            "LIFO Stack  —  Last In, First Out",
            "STACK"
        ))
        layout.addWidget(make_separator())

        # ── Capacity indicator ──
        cap_row = QHBoxLayout()
        cap_row.addWidget(self._lbl("Capacity:"))
        self.lbl_capacity = QLabel("0 / 20")
        cap_row.addWidget(self.lbl_capacity)
        cap_row.addStretch()

        self.lbl_top_pkg = QLabel("Top: —")
        cap_row.addWidget(self.lbl_top_pkg)
        layout.addLayout(cap_row)

        # ── Destination filter ──
        dest_row = QHBoxLayout()
        dest_row.addWidget(self._lbl("Next Delivery Stop:"))
        self.combo_deliver_dest = QComboBox()
        for dest in DESTINATIONS:
            self.combo_deliver_dest.addItem(f"  {dest}")
        dest_row.addWidget(self.combo_deliver_dest, stretch=1)
        layout.addLayout(dest_row)

        # ── Action buttons ──
        btn_row = QHBoxLayout()

        btn_deliver = QPushButton("  Deliver Next Package")
        btn_deliver.setObjectName("btn_primary")
        btn_deliver.clicked.connect(self._deliver_package)

        btn_deliver_dest = QPushButton("  Deliver All for Stop")
        btn_deliver_dest.setObjectName("btn_success")
        btn_deliver_dest.clicked.connect(self._deliver_for_destination)

        btn_row.addWidget(btn_deliver)
        btn_row.addWidget(btn_deliver_dest)
        layout.addLayout(btn_row)

        btn_row2 = QHBoxLayout()
        btn_unload_all = QPushButton("  Unload Entire Truck")
        btn_unload_all.setObjectName("btn_danger")
        btn_unload_all.clicked.connect(self._unload_all)
        btn_row2.addWidget(btn_unload_all)
        layout.addLayout(btn_row2)

        layout.addWidget(make_separator())

        # ── Optimization info ──
        opt_lbl = QLabel(
            "⚡ Optimization: Packages are loaded in destination order.\n"
            "   Use 'Deliver All for Stop' to unload only the current\n"
            "   stop's packages without re-sorting the whole truck."
        )
        opt_lbl.setWordWrap(True)
        layout.addWidget(opt_lbl)

        # ── Stack list ──
        stack_hdr = QHBoxLayout()
        stack_hdr.addWidget(self._lbl("Stack Contents  (top = next off):"))
        self.lbl_stack_count = QLabel("0 packages")
        stack_hdr.addStretch()
        stack_hdr.addWidget(self.lbl_stack_count)
        layout.addLayout(stack_hdr)

        self.list_stack = QListWidget()
        layout.addWidget(self.list_stack, stretch=1)

        # ── Delivered list ──
        layout.addWidget(self._lbl("  Recently Delivered:"))
        self.list_delivered = QListWidget()
        self.list_delivered.setMaximumHeight(120)
        layout.addWidget(self.list_delivered)

        return panel

    # ----------------------------------------------------------
    #  LOG BAR
    # ----------------------------------------------------------
    def _build_log_bar(self):
        bar = QWidget()
        bar.setFixedHeight(64)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 0, 4, 0)

        lbl = QLabel("EVENT LOG")
        layout.addWidget(lbl)

        self.list_log = QListWidget()
        self.list_log.setObjectName("log_list")
        self.list_log.setFlow(QListWidget.Flow.LeftToRight)
        self.list_log.setFixedHeight(52)
        layout.addWidget(self.list_log, stretch=1)

        return bar

    # ----------------------------------------------------------
    #  UTILITY WIDGETS
    # ----------------------------------------------------------
    def _lbl(self, text):
        l = QLabel(text)
        return l

    # ----------------------------------------------------------
    #  ACTION — Receive Order (ENQUEUE)
    # ----------------------------------------------------------
    def _receive_order(self):
        name = self.input_pkg_name.text().strip()
        if not name:
            self._show_warning("Please enter a package name.")
            return

        category_text = self.combo_category.currentText()
        category = category_text.split("  ", 1)[1]   # strip icon

        order = self.order_queue.enqueue(name, category)
        self.input_pkg_name.clear()

        self._log(f" Received  {order['id']} — {name} [{category}]", ACCENT)
        self._refresh_all()

    # ----------------------------------------------------------
    #  ACTION — Clear Queue
    # ----------------------------------------------------------
    def _clear_queue(self):
        if self.order_queue.is_empty():
            return
        count = self.order_queue.size()
        self.order_queue.queue.clear()
        self._log(f"  Queue cleared ({count} orders removed)", RED)
        self._refresh_all()

    # ----------------------------------------------------------
    #  ACTION — Move front of queue to Inventory (ARRAY store)
    # ----------------------------------------------------------
    def _move_queue_to_inventory(self):
        if self.order_queue.is_empty():
            self._show_warning("The order queue is empty.")
            return

        order = self.order_queue.dequeue()   # FIFO pop
        self.warehouse.store_package(order)  # Store in array[category_idx]

        idx = self.warehouse.get_aisle_index(order["category"])
        self._log(
            f" Stored  {order['id']} — {order['name']} → "
            f"Aisle [{idx}] {order['category']}", BLUE
        )
        self._refresh_all()

    # ----------------------------------------------------------
    #  ACTION — Check Shelf (ARRAY lookup by index)
    # ----------------------------------------------------------
    def _check_shelf(self):
        cat_text = self.combo_check_shelf.currentText()
        category = cat_text.split("  ", 1)[1]

        idx, packages = self.warehouse.check_shelf(category)
        icon = CATEGORY_ICONS[category]

        if not packages:
            result = f"  Aisle [{idx}]  {icon} {category}  —  EMPTY"
        else:
            names = ", ".join([p["name"] for p in packages[:3]])
            more = f" +{len(packages)-3} more" if len(packages) > 3 else ""
            result = (
                f"  Aisle [{idx}]  {icon} {category}\n"
                f"   {len(packages)} package(s): {names}{more}"
            )

        self.lbl_shelf_result.setText(result)
        self._log(f" Shelf check  Aisle [{idx}] {category}  —  {len(packages)} pkg(s)", BLUE)

    # ----------------------------------------------------------
    #  ACTION — Load Truck  (Inventory → Stack, with destination)
    # ----------------------------------------------------------
    def _load_truck(self):
        dest_text = self.combo_destination.currentText()
        destination = dest_text.split("  ", 1)[1]   # strip icon
        qty = self.spin_load_qty.value()

        loaded = 0
        failed_reason = ""

        # Pull packages from inventory across all aisles
        for cat in CATEGORIES:
            if loaded >= qty:
                break
            while loaded < qty:
                pkg = self.warehouse.remove_package_from_aisle(cat)
                if pkg is None:
                    break
                pkg["destination"] = destination
                success, reason = self.truck.push(pkg)   # LIFO push
                if not success:
                    # Truck full — return package to warehouse
                    self.warehouse.store_package(pkg)
                    failed_reason = reason
                    break
                loaded += 1

        if loaded == 0 and self.warehouse.total_packages() == 0:
            self._show_warning("Warehouse is empty. Receive and store orders first.")
        elif loaded == 0 and failed_reason:
            self._show_warning(failed_reason)
        else:
            self._log(
                f" Loaded {loaded} pkg(s) → Truck  [Dest: {destination}]", GREEN
            )

        self._refresh_all()

    # ----------------------------------------------------------
    #  ACTION — Deliver next package (POP from stack)
    # ----------------------------------------------------------
    def _deliver_package(self):
        if self.truck.is_empty():
            self._show_warning("Truck is empty.")
            return

        pkg = self.truck.pop()   # LIFO pop
        dest = pkg.get("destination", "Unknown")
        item_text = (
            f"  {pkg['id']} — {pkg['name']} [{pkg['category']}]  → {dest}"
        )
        self.list_delivered.insertItem(0, item_text)
        if self.list_delivered.count() > 20:
            self.list_delivered.takeItem(self.list_delivered.count() - 1)

        self._log(f" Delivered  {pkg['id']} — {pkg['name']}  →  {dest}", GREEN)
        self._refresh_all()

    # ----------------------------------------------------------
    #  ACTION — Deliver all packages for a specific stop
    #  OPTIMIZATION: Only pops packages matching the destination
    #  from the top; leaves the rest in order for subsequent stops.
    # ----------------------------------------------------------
    def _deliver_for_destination(self):
        if self.truck.is_empty():
            self._show_warning("Truck is empty.")
            return

        dest_text = self.combo_deliver_dest.currentText()
        dest = dest_text.split("  ", 1)[1]

        delivered = 0
        skipped   = []

        # Pop packages from top; if they match destination, deliver.
        # If they don't, temporarily hold them and re-push afterwards.
        while not self.truck.is_empty():
            pkg = self.truck.pop()
            if pkg.get("destination") == dest:
                item_text = (
                    f"  {pkg['id']} — {pkg['name']} [{pkg['category']}]  → {dest}"
                )
                self.list_delivered.insertItem(0, item_text)
                delivered += 1
            else:
                skipped.append(pkg)
                # OPTIMIZATION: stop looking once we pass this destination's block
                # (packages for other stops remain untouched lower in the stack)
                break

        # Re-push the non-matching packages in original order
        for pkg in reversed(skipped):
            self.truck.push(pkg)

        if delivered == 0:
            self._show_warning(
                f"No packages on top of stack are destined for {dest}.\n"
                f"The optimizer stops at the first non-matching package\n"
                f"to preserve loading order for other stops."
            )
        else:
            self._log(
                f" Delivered {delivered} pkg(s) for stop: {dest}  "
                f"({self.truck.size()} remain on truck)", GREEN
            )

        self._refresh_all()

    # ----------------------------------------------------------
    #  ACTION — Unload entire truck
    # ----------------------------------------------------------
    def _unload_all(self):
        if self.truck.is_empty():
            return
        count = self.truck.size()
        # Return packages to warehouse
        while not self.truck.is_empty():
            pkg = self.truck.pop()
            self.warehouse.store_package(pkg)
        self._log(f" Truck unloaded — {count} pkg(s) returned to warehouse", RED)
        self._refresh_all()

    # ----------------------------------------------------------
    #  REFRESH — Update all visual widgets
    # ----------------------------------------------------------
    def _refresh_all(self):
        self._refresh_queue()
        self._refresh_inventory()
        self._refresh_truck()
        self._refresh_stats()

    def _refresh_queue(self):
        self.list_queue.clear()
        items = self.order_queue.all_items()
        self.lbl_queue_count.setText(f"{len(items)} orders")

        for i, order in enumerate(items):
            icon = CATEGORY_ICONS[order["category"]]
            prefix = "→ " if i == 0 else f"  {i+1}. "
            text = (
                f"{prefix}{order['id']}  |  {order['name']}"
                f"  [{icon} {order['category']}]"
            )
            item = QListWidgetItem(text)
            if i == 0:
                item.setForeground(QColor(GREEN))
                item.setBackground(QColor(BG_CARD))
            self.list_queue.addItem(item)

        front = self.order_queue.peek()
        if front:
            icon = CATEGORY_ICONS[front["category"]]
            self.lbl_queue_front.setText(
                f"{front['id']} — {front['name']} [{icon} {front['category']}]"
            )
        else:
            self.lbl_queue_front.setText("Queue is empty")

    def _refresh_inventory(self):
        for cat in CATEGORIES:
            count_lbl, pkg_list = self.shelf_widgets[cat]
            packages = self.warehouse.get_packages_in_aisle(cat)
            count_lbl.setText(f"{len(packages)} pkgs")
            pkg_list.clear()
            for pkg in packages:
                pkg_list.addItem(f"  {pkg['id']}  {pkg['name']}")

    def _refresh_truck(self):
        self.list_stack.clear()
        items = self.truck.all_items()   # reversed (top first)
        self.lbl_stack_count.setText(f"{len(items)} packages")

        cap = self.truck.size()
        color = GREEN if cap < 15 else ACCENT if cap < 20 else RED
        self.lbl_capacity.setText(f"{cap} / 20")

        for i, pkg in enumerate(items):
            dest = pkg.get("destination", "?")
            icon = CATEGORY_ICONS[pkg["category"]]
            prefix = "▶ TOP  " if i == 0 else f"   {i+1}.    "
            text = (
                f"{prefix}{pkg['id']}  |  {pkg['name']}"
                f"  [{icon} {pkg['category']}]  → {dest}"
            )
            item = QListWidgetItem(text)
            if i == 0:
                item.setForeground(QColor(ACCENT))
                item.setBackground(QColor(BG_CARD))
            self.list_stack.addItem(item)

        top = self.truck.peek()
        if top:
            self.lbl_top_pkg.setText(
                f"Top: {top['id']} — {top['name']} → {top.get('destination','?')}"
            )
        else:
            self.lbl_top_pkg.setText("Top: — (empty)")

    def _refresh_stats(self):
        total_received = self.order_queue.order_counter - 1
        self.stat_orders._val_label.setText(str(total_received))
        self.stat_stored._val_label.setText(str(self.warehouse.total_packages()))
        self.stat_truck._val_label.setText(str(self.truck.size()))

    # ----------------------------------------------------------
    #  LOGGER
    # ----------------------------------------------------------
    def _log(self, message, color=TEXT_DIM):
        item = QListWidgetItem(message)
        item.setForeground(QColor(color))
        self.list_log.insertItem(0, item)
        if self.list_log.count() > 50:
            self.list_log.takeItem(self.list_log.count() - 1)

    # ----------------------------------------------------------
    #  UTILITIES
    # ----------------------------------------------------------
    def _show_warning(self, msg):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Amazon Hub")
        dlg.setText(msg)
        dlg.setIcon(QMessageBox.Icon.Warning)
        dlg.exec()

    # ----------------------------------------------------------
    #  DEMO DATA
    # ----------------------------------------------------------
    def _load_demo_data(self):
        demo_orders = [
            ("Galaxy S25 Phone",   "Electronics"),
            ("Running Shoes",      "Clothing"),
            ("Python Cookbook",    "Books"),
            ("Organic Apples x6",  "Food"),
            ("LEGO Technic Set",   "Toys"),
            ("Air Fryer 5L",       "Appliances"),
            ("Wireless Headset",   "Electronics"),
            ("Winter Jacket",      "Clothing"),
        ]
        for name, cat in demo_orders:
            self.order_queue.enqueue(name, cat)

        # Pre-store some items in warehouse
        for _ in range(4):
            order = self.order_queue.dequeue()
            if order:
                self.warehouse.store_package(order)

        self._refresh_all()


# ==============================================================
#  ENTRY POINT
# ==============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Amazon Hub Simulator")

    window = AmazonHubSimulator()
    window.show()

    sys.exit(app.exec())