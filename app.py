"""
SAP P2P (Procure-to-Pay) Simulator
====================================
Company: TechBridge Manufacturing Pvt. Ltd.
Run: python app.py   then open http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3, os, datetime

app = Flask(__name__)
app.secret_key = "sap_p2p_kiit_2026"
DB = "sap_p2p.db"

# ─────────────────────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS materials (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        mat_no      TEXT UNIQUE NOT NULL,
        description TEXT NOT NULL,
        mat_type    TEXT NOT NULL,
        uom         TEXT NOT NULL,
        val_class   TEXT NOT NULL,
        plant       TEXT DEFAULT 'TB10',
        stock_qty   REAL DEFAULT 0,
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS vendors (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_no   TEXT UNIQUE NOT NULL,
        name        TEXT NOT NULL,
        city        TEXT NOT NULL,
        gstin       TEXT,
        payment_term TEXT NOT NULL,
        recon_acct  TEXT DEFAULT '160000',
        email       TEXT,
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS purchase_info_records (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        mat_no      TEXT NOT NULL,
        vendor_no   TEXT NOT NULL,
        price       REAL NOT NULL,
        currency    TEXT DEFAULT 'INR',
        delivery_days INTEGER NOT NULL,
        min_qty     REAL NOT NULL,
        uom         TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS purchase_requisitions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        pr_no       TEXT UNIQUE NOT NULL,
        mat_no      TEXT NOT NULL,
        qty         REAL NOT NULL,
        uom         TEXT NOT NULL,
        required_date TEXT NOT NULL,
        plant       TEXT DEFAULT 'TB10',
        cost_center TEXT DEFAULT 'CC1001',
        gl_account  TEXT DEFAULT '400000',
        status      TEXT DEFAULT 'Open',
        requestor   TEXT NOT NULL,
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS rfqs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        rfq_no      TEXT UNIQUE NOT NULL,
        pr_no       TEXT NOT NULL,
        mat_no      TEXT NOT NULL,
        qty         REAL NOT NULL,
        uom         TEXT NOT NULL,
        deadline    TEXT NOT NULL,
        status      TEXT DEFAULT 'Sent',
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS rfq_vendors (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        rfq_no      TEXT NOT NULL,
        vendor_no   TEXT NOT NULL,
        quoted_price REAL DEFAULT 0,
        quoted_qty  REAL DEFAULT 0,
        delivery_days INTEGER DEFAULT 0,
        status      TEXT DEFAULT 'Pending'
    );

    CREATE TABLE IF NOT EXISTS purchase_orders (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        po_no       TEXT UNIQUE NOT NULL,
        pr_no       TEXT,
        rfq_no      TEXT,
        vendor_no   TEXT NOT NULL,
        mat_no      TEXT NOT NULL,
        qty         REAL NOT NULL,
        uom         TEXT NOT NULL,
        unit_price  REAL NOT NULL,
        total_value REAL NOT NULL,
        currency    TEXT DEFAULT 'INR',
        delivery_date TEXT NOT NULL,
        plant       TEXT DEFAULT 'TB10',
        payment_term TEXT DEFAULT 'NT30',
        status      TEXT DEFAULT 'Open',
        gr_qty      REAL DEFAULT 0,
        inv_qty     REAL DEFAULT 0,
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS goods_receipts (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        gr_no       TEXT UNIQUE NOT NULL,
        po_no       TEXT NOT NULL,
        mat_no      TEXT NOT NULL,
        vendor_no   TEXT NOT NULL,
        recv_qty    REAL NOT NULL,
        uom         TEXT NOT NULL,
        movement_type TEXT DEFAULT '101',
        storage_loc TEXT DEFAULT 'RW01',
        plant       TEXT DEFAULT 'TB10',
        posting_date TEXT NOT NULL,
        debit_acct  TEXT DEFAULT 'BSX (RM Stock)',
        credit_acct TEXT DEFAULT 'WRX (GR/IR)',
        amount      REAL NOT NULL,
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS invoices (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        inv_no      TEXT UNIQUE NOT NULL,
        po_no       TEXT NOT NULL,
        gr_no       TEXT NOT NULL,
        vendor_no   TEXT NOT NULL,
        inv_qty     REAL NOT NULL,
        unit_price  REAL NOT NULL,
        inv_amount  REAL NOT NULL,
        tax_amount  REAL DEFAULT 0,
        total_amount REAL NOT NULL,
        currency    TEXT DEFAULT 'INR',
        posting_date TEXT NOT NULL,
        baseline_date TEXT NOT NULL,
        due_date    TEXT NOT NULL,
        match_status TEXT DEFAULT 'Matched',
        status      TEXT DEFAULT 'Open',
        debit_acct  TEXT DEFAULT 'WRX (GR/IR)',
        credit_acct TEXT DEFAULT '160000 (AP)',
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS payments (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        pay_no      TEXT UNIQUE NOT NULL,
        inv_no      TEXT NOT NULL,
        vendor_no   TEXT NOT NULL,
        pay_amount  REAL NOT NULL,
        pay_method  TEXT DEFAULT 'Bank Transfer',
        bank_acct   TEXT DEFAULT '113100',
        pay_date    TEXT NOT NULL,
        debit_acct  TEXT DEFAULT '160000 (AP)',
        credit_acct TEXT DEFAULT '113100 (Bank)',
        status      TEXT DEFAULT 'Paid',
        created_at  TEXT DEFAULT (datetime('now'))
    );
    """)

    # ── Seed initial master data if empty ───────────────────────
    if not c.execute("SELECT 1 FROM materials LIMIT 1").fetchone():
        c.executemany("INSERT INTO materials(mat_no,description,mat_type,uom,val_class) VALUES (?,?,?,?,?)", [
            ("TB-RM-001","Copper Wire Roll","ROH - Raw Material","KG","3000"),
            ("TB-RM-002","PCB Board","ROH - Raw Material","EA","3000"),
            ("TB-CS-001","Machine Lubricant","HIBE - Consumable","LT","3001"),
        ])

    if not c.execute("SELECT 1 FROM vendors LIMIT 1").fetchone():
        c.executemany("INSERT INTO vendors(vendor_no,name,city,gstin,payment_term,email) VALUES (?,?,?,?,?,?)", [
            ("V-1001","Electronica Components Ltd.","Mumbai","27AAACE4999Q1ZK","NT30","sales@electronica.com"),
            ("V-1002","CopperTech Supplies","Chennai","33AABCC1234D1ZT","NT15","orders@coppertech.com"),
            ("V-1003","Bharat Industrial Corp.","Pune","27AABCB5678E2ZP","NT45","procurement@bic.in"),
        ])

    if not c.execute("SELECT 1 FROM purchase_info_records LIMIT 1").fetchone():
        c.executemany("INSERT INTO purchase_info_records(mat_no,vendor_no,price,delivery_days,min_qty,uom) VALUES (?,?,?,?,?,?)", [
            ("TB-RM-001","V-1002",850.0,7,50,"KG"),
            ("TB-RM-002","V-1001",1200.0,10,100,"EA"),
            ("TB-CS-001","V-1003",350.0,5,20,"LT"),
        ])

    conn.commit()
    conn.close()

# ── Auto-generate document numbers ──────────────────────────
def next_doc_no(prefix, table, col):
    conn = get_db()
    row = conn.execute(f"SELECT {col} FROM {table} ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if row:
        last = int(row[0].replace(prefix,""))
        return f"{prefix}{last+1:010d}"
    return f"{prefix}0000000001"

def today():
    return datetime.date.today().isoformat()

def due_date(baseline, days):
    d = datetime.date.fromisoformat(baseline) + datetime.timedelta(days=days)
    return d.isoformat()

# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    conn = get_db()
    stats = {
        "materials": conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0],
        "vendors":   conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0],
        "pr_open":   conn.execute("SELECT COUNT(*) FROM purchase_requisitions WHERE status='Open'").fetchone()[0],
        "po_open":   conn.execute("SELECT COUNT(*) FROM purchase_orders WHERE status='Open'").fetchone()[0],
        "inv_open":  conn.execute("SELECT COUNT(*) FROM invoices WHERE status='Open'").fetchone()[0],
        "gr_count":  conn.execute("SELECT COUNT(*) FROM goods_receipts").fetchone()[0],
        "pay_count": conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0],
        "total_spend": conn.execute("SELECT COALESCE(SUM(pay_amount),0) FROM payments").fetchone()[0],
    }
    recent_pos = conn.execute("""
        SELECT po.po_no, v.name, m.description, po.total_value, po.status, po.created_at
        FROM purchase_orders po
        JOIN vendors v ON po.vendor_no=v.vendor_no
        JOIN materials m ON po.mat_no=m.mat_no
        ORDER BY po.id DESC LIMIT 5
    """).fetchall()
    conn.close()
    return render_template("dashboard.html", stats=stats, recent_pos=recent_pos)


# ── MATERIAL MASTER ──────────────────────────────────────────
@app.route("/materials")
def materials():
    conn = get_db()
    rows = conn.execute("SELECT * FROM materials ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("materials.html", rows=rows)

@app.route("/materials/create", methods=["GET","POST"])
def create_material():
    if request.method == "POST":
        conn = get_db()
        try:
            conn.execute("INSERT INTO materials(mat_no,description,mat_type,uom,val_class) VALUES(?,?,?,?,?)",
                (request.form["mat_no"], request.form["description"],
                 request.form["mat_type"], request.form["uom"], request.form["val_class"]))
            conn.commit()
            flash(f"Material {request.form['mat_no']} created successfully!", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        conn.close()
        return redirect(url_for("materials"))
    return render_template("material_form.html")


# ── VENDOR MASTER ────────────────────────────────────────────
@app.route("/vendors")
def vendors():
    conn = get_db()
    rows = conn.execute("SELECT * FROM vendors ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("vendors.html", rows=rows)

@app.route("/vendors/create", methods=["GET","POST"])
def create_vendor():
    if request.method == "POST":
        conn = get_db()
        try:
            conn.execute("INSERT INTO vendors(vendor_no,name,city,gstin,payment_term,email) VALUES(?,?,?,?,?,?)",
                (request.form["vendor_no"], request.form["name"], request.form["city"],
                 request.form["gstin"], request.form["payment_term"], request.form["email"]))
            conn.commit()
            flash(f"Vendor {request.form['vendor_no']} — {request.form['name']} created!", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        conn.close()
        return redirect(url_for("vendors"))
    return render_template("vendor_form.html")


# ── PURCHASE REQUISITION (ME51N equivalent) ──────────────────
@app.route("/pr")
def pr_list():
    conn = get_db()
    rows = conn.execute("""
        SELECT pr.*, m.description as mat_desc, m.uom
        FROM purchase_requisitions pr
        JOIN materials m ON pr.mat_no=m.mat_no
        ORDER BY pr.id DESC
    """).fetchall()
    conn.close()
    return render_template("pr_list.html", rows=rows)

@app.route("/pr/create", methods=["GET","POST"])
def create_pr():
    conn = get_db()
    materials_list = conn.execute("SELECT * FROM materials").fetchall()
    if request.method == "POST":
        pr_no = next_doc_no("PR", "purchase_requisitions", "pr_no")
        try:
            conn.execute("""INSERT INTO purchase_requisitions
                (pr_no,mat_no,qty,uom,required_date,plant,cost_center,gl_account,requestor)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (pr_no, request.form["mat_no"], float(request.form["qty"]),
                 request.form["uom"], request.form["required_date"],
                 request.form.get("plant","TB10"), request.form.get("cost_center","CC1001"),
                 request.form.get("gl_account","400000"), request.form["requestor"]))
            conn.commit()
            flash(f"✅ Purchase Requisition {pr_no} created successfully!", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        conn.close()
        return redirect(url_for("pr_list"))
    conn.close()
    return render_template("pr_form.html", materials=materials_list, today=today())

@app.route("/pr/approve/<pr_no>")
def approve_pr(pr_no):
    conn = get_db()
    conn.execute("UPDATE purchase_requisitions SET status='Approved' WHERE pr_no=?", (pr_no,))
    conn.commit()
    conn.close()
    flash(f"PR {pr_no} approved!", "success")
    return redirect(url_for("pr_list"))


# ── RFQ (ME41 equivalent) ────────────────────────────────────
@app.route("/rfq")
def rfq_list():
    conn = get_db()
    rows = conn.execute("""
        SELECT r.*, m.description, pr.requestor
        FROM rfqs r
        JOIN materials m ON r.mat_no=m.mat_no
        JOIN purchase_requisitions pr ON r.pr_no=pr.pr_no
        ORDER BY r.id DESC
    """).fetchall()
    conn.close()
    return render_template("rfq_list.html", rows=rows)

@app.route("/rfq/create", methods=["GET","POST"])
def create_rfq():
    conn = get_db()
    prs = conn.execute("SELECT * FROM purchase_requisitions WHERE status='Approved'").fetchall()
    vendors_list = conn.execute("SELECT * FROM vendors").fetchall()
    if request.method == "POST":
        rfq_no = next_doc_no("RFQ", "rfqs", "rfq_no")
        pr_no  = request.form["pr_no"]
        pr     = conn.execute("SELECT * FROM purchase_requisitions WHERE pr_no=?", (pr_no,)).fetchone()
        try:
            conn.execute("""INSERT INTO rfqs(rfq_no,pr_no,mat_no,qty,uom,deadline)
                VALUES(?,?,?,?,?,?)""",
                (rfq_no, pr_no, pr["mat_no"], pr["qty"], pr["uom"], request.form["deadline"]))
            vendor_ids = request.form.getlist("vendors")
            for v in vendor_ids:
                conn.execute("INSERT INTO rfq_vendors(rfq_no,vendor_no) VALUES(?,?)", (rfq_no, v))
            conn.commit()
            flash(f"✅ RFQ {rfq_no} sent to {len(vendor_ids)} vendor(s)!", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        conn.close()
        return redirect(url_for("rfq_list"))
    conn.close()
    return render_template("rfq_form.html", prs=prs, vendors=vendors_list,
                           today=today(), deadline=due_date(today(),7))

@app.route("/rfq/quotation/<rfq_no>", methods=["GET","POST"])
def enter_quotation(rfq_no):
    conn = get_db()
    rfq = conn.execute("SELECT r.*, m.description FROM rfqs r JOIN materials m ON r.mat_no=m.mat_no WHERE rfq_no=?", (rfq_no,)).fetchone()
    rv  = conn.execute("""
        SELECT rv.*, v.name, v.city
        FROM rfq_vendors rv JOIN vendors v ON rv.vendor_no=v.vendor_no
        WHERE rfq_no=?
    """, (rfq_no,)).fetchall()
    if request.method == "POST":
        for v in rv:
            price = request.form.get(f"price_{v['vendor_no']}", 0)
            days  = request.form.get(f"days_{v['vendor_no']}", 0)
            conn.execute("""UPDATE rfq_vendors SET quoted_price=?, delivery_days=?, status='Quoted',
                quoted_qty=? WHERE rfq_no=? AND vendor_no=?""",
                (float(price), int(days), float(rfq["qty"]), rfq_no, v["vendor_no"]))
        conn.execute("UPDATE rfqs SET status='Quoted' WHERE rfq_no=?", (rfq_no,))
        conn.commit()
        conn.close()
        flash(f"✅ Quotations recorded for RFQ {rfq_no}", "success")
        return redirect(url_for("rfq_compare", rfq_no=rfq_no))
    conn.close()
    return render_template("quotation_form.html", rfq=rfq, rv=rv)

@app.route("/rfq/compare/<rfq_no>")
def rfq_compare(rfq_no):
    conn = get_db()
    rfq = conn.execute("SELECT r.*, m.description FROM rfqs r JOIN materials m ON r.mat_no=m.mat_no WHERE rfq_no=?", (rfq_no,)).fetchone()
    rv  = conn.execute("""
        SELECT rv.*, v.name, v.city, v.payment_term
        FROM rfq_vendors rv JOIN vendors v ON rv.vendor_no=v.vendor_no
        WHERE rfq_no=? ORDER BY quoted_price ASC
    """, (rfq_no,)).fetchall()
    conn.close()
    return render_template("rfq_compare.html", rfq=rfq, rv=rv)


# ── PURCHASE ORDER (ME21N equivalent) ───────────────────────
@app.route("/po")
def po_list():
    conn = get_db()
    rows = conn.execute("""
        SELECT po.*, v.name as vendor_name, m.description as mat_desc
        FROM purchase_orders po
        JOIN vendors v ON po.vendor_no=v.vendor_no
        JOIN materials m ON po.mat_no=m.mat_no
        ORDER BY po.id DESC
    """).fetchall()
    conn.close()
    return render_template("po_list.html", rows=rows)

@app.route("/po/create", methods=["GET","POST"])
def create_po():
    conn = get_db()
    prs      = conn.execute("SELECT * FROM purchase_requisitions WHERE status='Approved'").fetchall()
    rfqs_list= conn.execute("SELECT rfq_no,mat_no FROM rfqs WHERE status='Quoted'").fetchall()
    vendors_list = conn.execute("SELECT * FROM vendors").fetchall()
    materials_list = conn.execute("SELECT * FROM materials").fetchall()
    pirs     = conn.execute("SELECT * FROM purchase_info_records").fetchall()

    if request.method == "POST":
        po_no = next_doc_no("PO", "purchase_orders", "po_no")
        qty   = float(request.form["qty"])
        price = float(request.form["unit_price"])
        total = round(qty * price, 2)
        try:
            conn.execute("""INSERT INTO purchase_orders
                (po_no,pr_no,rfq_no,vendor_no,mat_no,qty,uom,unit_price,total_value,
                 delivery_date,plant,payment_term,status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (po_no, request.form.get("pr_no"), request.form.get("rfq_no"),
                 request.form["vendor_no"], request.form["mat_no"],
                 qty, request.form["uom"], price, total,
                 request.form["delivery_date"], request.form.get("plant","TB10"),
                 request.form.get("payment_term","NT30"), "Open"))
            if request.form.get("pr_no"):
                conn.execute("UPDATE purchase_requisitions SET status='PO Created' WHERE pr_no=?",
                             (request.form.get("pr_no"),))
            conn.commit()
            flash(f"✅ Purchase Order {po_no} created! Total Value: INR {total:,.2f}", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        conn.close()
        return redirect(url_for("po_list"))
    conn.close()
    return render_template("po_form.html", prs=prs, rfqs=rfqs_list,
                           vendors=vendors_list, materials=materials_list,
                           pirs=pirs, today=today(),
                           delivery=due_date(today(),10))

@app.route("/po/view/<po_no>")
def view_po(po_no):
    conn = get_db()
    po = conn.execute("""
        SELECT po.*, v.name, v.city, v.email, v.gstin, v.payment_term as v_payment,
               m.description, m.mat_type
        FROM purchase_orders po
        JOIN vendors v ON po.vendor_no=v.vendor_no
        JOIN materials m ON po.mat_no=m.mat_no
        WHERE po.po_no=?
    """, (po_no,)).fetchone()
    grs = conn.execute("SELECT * FROM goods_receipts WHERE po_no=?", (po_no,)).fetchall()
    invs= conn.execute("SELECT * FROM invoices WHERE po_no=?", (po_no,)).fetchall()
    conn.close()
    return render_template("po_view.html", po=po, grs=grs, invs=invs)


# ── GOODS RECEIPT (MIGO equivalent) ─────────────────────────
@app.route("/gr")
def gr_list():
    conn = get_db()
    rows = conn.execute("""
        SELECT gr.*, v.name as vendor_name, m.description as mat_desc
        FROM goods_receipts gr
        JOIN vendors v ON gr.vendor_no=v.vendor_no
        JOIN materials m ON gr.mat_no=m.mat_no
        ORDER BY gr.id DESC
    """).fetchall()
    conn.close()
    return render_template("gr_list.html", rows=rows)

@app.route("/gr/create", methods=["GET","POST"])
def create_gr():
    conn = get_db()
    open_pos = conn.execute("""
        SELECT po.*, v.name, m.description, (po.qty - po.gr_qty) as pending_qty
        FROM purchase_orders po
        JOIN vendors v ON po.vendor_no=v.vendor_no
        JOIN materials m ON po.mat_no=m.mat_no
        WHERE po.status IN ('Open','Partial GR') AND po.qty > po.gr_qty
    """).fetchall()

    if request.method == "POST":
        gr_no  = next_doc_no("GR", "goods_receipts", "gr_no")
        po_no  = request.form["po_no"]
        po     = conn.execute("SELECT * FROM purchase_orders WHERE po_no=?", (po_no,)).fetchone()
        qty    = float(request.form["recv_qty"])
        amount = round(qty * po["unit_price"], 2)
        try:
            conn.execute("""INSERT INTO goods_receipts
                (gr_no,po_no,mat_no,vendor_no,recv_qty,uom,storage_loc,posting_date,amount)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (gr_no, po_no, po["mat_no"], po["vendor_no"],
                 qty, po["uom"], request.form.get("storage_loc","RW01"),
                 request.form["posting_date"], amount))
            new_gr_qty = po["gr_qty"] + qty
            new_status = "GR Done" if new_gr_qty >= po["qty"] else "Partial GR"
            conn.execute("UPDATE purchase_orders SET gr_qty=?, status=? WHERE po_no=?",
                         (new_gr_qty, new_status, po_no))
            conn.execute("UPDATE materials SET stock_qty=stock_qty+? WHERE mat_no=?",
                         (qty, po["mat_no"]))
            conn.commit()
            flash(f"✅ Goods Receipt {gr_no} posted! {qty} {po['uom']} received. "
                  f"Stock updated. Debit: BSX | Credit: WRX/GR-IR", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        conn.close()
        return redirect(url_for("gr_list"))
    conn.close()
    return render_template("gr_form.html", open_pos=open_pos, today=today())


# ── INVOICE VERIFICATION (MIRO equivalent) ──────────────────
@app.route("/invoice")
def invoice_list():
    conn = get_db()
    rows = conn.execute("""
        SELECT inv.*, v.name as vendor_name, po.mat_no
        FROM invoices inv
        JOIN vendors v ON inv.vendor_no=v.vendor_no
        JOIN purchase_orders po ON inv.po_no=po.po_no
        ORDER BY inv.id DESC
    """).fetchall()
    conn.close()
    return render_template("invoice_list.html", rows=rows)

@app.route("/invoice/create", methods=["GET","POST"])
def create_invoice():
    conn = get_db()
    grs = conn.execute("""
        SELECT gr.*, v.name, v.payment_term, po.unit_price, po.payment_term as po_pt,
               m.description
        FROM goods_receipts gr
        JOIN purchase_orders po ON gr.po_no=po.po_no
        JOIN vendors v ON gr.vendor_no=v.vendor_no
        JOIN materials m ON gr.mat_no=m.mat_no
        WHERE gr.gr_no NOT IN (SELECT gr_no FROM invoices)
    """).fetchall()

    if request.method == "POST":
        inv_no = next_doc_no("INV", "invoices", "inv_no")
        gr_no  = request.form["gr_no"]
        gr     = conn.execute("SELECT * FROM goods_receipts WHERE gr_no=?", (gr_no,)).fetchone()
        po     = conn.execute("SELECT * FROM purchase_orders WHERE po_no=?", (gr["po_no"],)).fetchone()
        vendor = conn.execute("SELECT * FROM vendors WHERE vendor_no=?", (gr["vendor_no"],)).fetchone()

        inv_qty   = float(request.form.get("inv_qty", gr["recv_qty"]))
        unit_price= float(request.form.get("unit_price", po["unit_price"]))
        inv_amount= round(inv_qty * unit_price, 2)
        tax_pct   = float(request.form.get("tax_pct", 18))
        tax_amount= round(inv_amount * tax_pct / 100, 2)
        total     = round(inv_amount + tax_amount, 2)

        pt_days = {"NT15":15,"NT30":30,"NT45":45}.get(vendor["payment_term"], 30)
        baseline = request.form["posting_date"]
        due      = due_date(baseline, pt_days)

        # 3-way match check
        match_status = "Matched"
        if abs(inv_qty - gr["recv_qty"]) > 0.001:
            match_status = "Qty Variance"
        elif abs(unit_price - po["unit_price"]) > 0.01:
            match_status = "Price Variance"

        try:
            conn.execute("""INSERT INTO invoices
                (inv_no,po_no,gr_no,vendor_no,inv_qty,unit_price,inv_amount,
                 tax_amount,total_amount,posting_date,baseline_date,due_date,
                 match_status,status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (inv_no, gr["po_no"], gr_no, gr["vendor_no"],
                 inv_qty, unit_price, inv_amount, tax_amount, total,
                 baseline, baseline, due, match_status, "Open"))
            conn.execute("UPDATE purchase_orders SET inv_qty=inv_qty+? WHERE po_no=?",
                         (inv_qty, gr["po_no"]))
            conn.commit()
            flash(f"✅ Invoice {inv_no} posted! 3-Way Match: {match_status}. "
                  f"Due Date: {due}. Amount: INR {total:,.2f}", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        conn.close()
        return redirect(url_for("invoice_list"))
    conn.close()
    return render_template("invoice_form.html", grs=grs, today=today())


# ── PAYMENT (F110 / F-53 equivalent) ────────────────────────
@app.route("/payment")
def payment_list():
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*, v.name as vendor_name, inv.due_date, inv.match_status
        FROM payments p
        JOIN vendors v ON p.vendor_no=v.vendor_no
        JOIN invoices inv ON p.inv_no=inv.inv_no
        ORDER BY p.id DESC
    """).fetchall()
    conn.close()
    return render_template("payment_list.html", rows=rows)

@app.route("/payment/create", methods=["GET","POST"])
def create_payment():
    conn = get_db()
    due_invs = conn.execute("""
        SELECT inv.*, v.name, v.payment_term
        FROM invoices inv
        JOIN vendors v ON inv.vendor_no=v.vendor_no
        WHERE inv.status='Open' AND inv.match_status='Matched'
    """).fetchall()

    if request.method == "POST":
        pay_no = next_doc_no("PAY", "payments", "pay_no")
        inv_no = request.form["inv_no"]
        inv    = conn.execute("SELECT * FROM invoices WHERE inv_no=?", (inv_no,)).fetchone()
        amount = float(request.form.get("pay_amount", inv["total_amount"]))
        try:
            conn.execute("""INSERT INTO payments
                (pay_no,inv_no,vendor_no,pay_amount,pay_method,pay_date)
                VALUES(?,?,?,?,?,?)""",
                (pay_no, inv_no, inv["vendor_no"], amount,
                 request.form.get("pay_method","Bank Transfer"),
                 request.form["pay_date"]))
            conn.execute("UPDATE invoices SET status='Paid' WHERE inv_no=?", (inv_no,))
            po_no = inv["po_no"]
            remaining = conn.execute(
                "SELECT COUNT(*) FROM invoices WHERE po_no=? AND status='Open'", (po_no,)).fetchone()[0]
            if remaining == 0:
                conn.execute("UPDATE purchase_orders SET status='Completed' WHERE po_no=?", (po_no,))
            conn.commit()
            flash(f"✅ Payment {pay_no} processed! INR {amount:,.2f} paid to vendor. "
                  f"Debit: AP 160000 | Credit: Bank 113100. P2P Cycle COMPLETE! 🎉", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        conn.close()
        return redirect(url_for("payment_list"))
    conn.close()
    return render_template("payment_form.html", due_invs=due_invs, today=today())


# ── REPORTS ──────────────────────────────────────────────────
@app.route("/reports")
def reports():
    conn = get_db()
    # Stock overview (MB52)
    stock = conn.execute("SELECT mat_no,description,mat_type,uom,stock_qty FROM materials").fetchall()
    # PO by vendor (ME2L)
    po_by_vendor = conn.execute("""
        SELECT v.name, COUNT(po.id) as po_count,
               SUM(po.total_value) as total_val,
               SUM(CASE WHEN po.status='Completed' THEN 1 ELSE 0 END) as completed
        FROM purchase_orders po JOIN vendors v ON po.vendor_no=v.vendor_no
        GROUP BY po.vendor_no
    """).fetchall()
    # Vendor AP (FBL1N)
    vendor_ap = conn.execute("""
        SELECT v.name, v.vendor_no,
               SUM(CASE WHEN inv.status='Open' THEN inv.total_amount ELSE 0 END) as open_amt,
               SUM(CASE WHEN inv.status='Paid' THEN inv.total_amount ELSE 0 END) as paid_amt
        FROM invoices inv JOIN vendors v ON inv.vendor_no=v.vendor_no
        GROUP BY inv.vendor_no
    """).fetchall()
    # Monthly spend
    monthly = conn.execute("""
        SELECT strftime('%Y-%m', pay_date) as month, SUM(pay_amount) as total
        FROM payments GROUP BY month ORDER BY month
    """).fetchall()
    conn.close()
    return render_template("reports.html", stock=stock, po_by_vendor=po_by_vendor,
                           vendor_ap=vendor_ap, monthly=monthly)

# API for PIR price lookup
@app.route("/api/pir/<mat_no>/<vendor_no>")
def get_pir(mat_no, vendor_no):
    conn = get_db()
    pir = conn.execute("SELECT * FROM purchase_info_records WHERE mat_no=? AND vendor_no=?",
                       (mat_no, vendor_no)).fetchone()
    conn.close()
    if pir:
        return jsonify({"price": pir["price"], "uom": pir["uom"], "delivery_days": pir["delivery_days"]})
    return jsonify({"price": 0, "uom": "", "delivery_days": 0})

@app.route("/api/material/<mat_no>")
def get_material(mat_no):
    conn = get_db()
    m = conn.execute("SELECT * FROM materials WHERE mat_no=?", (mat_no,)).fetchone()
    conn.close()
    if m:
        return jsonify({"uom": m["uom"], "description": m["description"]})
    return jsonify({})

if __name__ == "__main__":
    init_db()
    print("\n" + "="*60)
    print("  SAP P2P Simulator — TechBridge Manufacturing")
    print("="*60)
    print("  Open your browser: http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(debug=True)
