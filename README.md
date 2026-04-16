# SAP P2P Simulator 
## Procure-to-Pay Full Purchasing Cycle | KIIT SAP Capstone Project

---

## WHAT IS THIS?
A fully working web application that simulates the complete SAP MM
Procure-to-Pay (P2P) cycle. Built with Python Flask + SQLite.
Runs 100% on your laptop — NO SAP license needed.

---

## WHERE TO RUN IT

### On Windows:
1. Open Command Prompt (cmd) or PowerShell
2. Navigate to this folder:  cd C:\path\to\sap_p2p
3. Follow the steps below

### On Mac/Linux:
1. Open Terminal
2. Navigate to this folder:  cd /path/to/sap_p2p
3. Follow the steps below

---

## SETUP — ONE TIME ONLY

### Step 1: Install Python
Download from https://www.python.org/downloads/
Make sure to check "Add Python to PATH" during installation.
Verify: open cmd and type:  python --version

### Step 2: Install Flask
Open cmd/terminal in the sap_p2p folder and run:
    pip install flask

OR using the requirements file:
    pip install -r requirements.txt

---

## RUN THE PROJECT

### Step 3: Start the Server
In cmd/terminal (inside the sap_p2p folder):
    python app.py

You will see:
    ============================================================
      SAP P2P Simulator — TechBridge Manufacturing
    ============================================================
      Open your browser: http://127.0.0.1:5000
    ============================================================

### Step 4: Open Your Browser
Go to:   http://127.0.0.1:5000
The app opens with a full dashboard!

### Step 5: Stop the Server
Press  Ctrl + C  in the terminal to stop.

---

## THE COMPLETE P2P CYCLE — FOLLOW THIS ORDER

The app comes preloaded with:
  - 3 Materials (Copper Wire, PCB Board, Machine Lubricant)
  - 3 Vendors (Electronica, CopperTech, Bharat Industrial)
  - Purchasing Info Records with agreed prices

### Follow these 7 steps in order:

STEP 1: Purchase Requisition (ME51N)
  → Click "Purchase Req." in sidebar → "Create PR"
  → Select material, enter quantity, set required date
  → Click "Create PR"
  → On the list, click "Approve" to approve the PR

STEP 2: Request for Quotation (ME41)
  → Click "RFQ" → "Create RFQ"
  → Select the approved PR, set deadline
  → Check at least 2-3 vendors → "Send RFQ"
  → On RFQ list, click "Enter Quotes"
  → Enter price and delivery days for each vendor
  → After saving, click "Compare" to see ME49 Price Comparison

STEP 3: Purchase Order (ME21N)
  → From the comparison screen, click "Create PO" for the winner
  → OR go to "Purchase Order" → "Create PO"
  → Vendor price is auto-filled from PIR if available
  → Total value auto-calculated
  → Click "Create PO"

STEP 4: Goods Receipt (MIGO)
  → Click "Goods Receipt" → "Post GR"
  → Select the PO, enter received quantity
  → System auto-calculates: Debit BSX (Stock), Credit WRX (GR/IR)
  → Click "Post GR" — stock is updated automatically

STEP 5: Invoice Verification (MIRO)
  → Click "Invoice Verify" → "Post Invoice"
  → Select the GR just posted
  → Enter vendor invoice quantity and price
  → System performs 3-WAY MATCH (PO + GR + Invoice)
  → If matched: green "Matched" badge
  → If price differs: "Price Variance" warning
  → Click "Post Invoice" — AP ledger is updated

STEP 6: Payment (F110)
  → Click "Payment" → "Process Payment"
  → Select the open invoice (only Matched invoices appear)
  → Enter payment amount and date
  → System: Debit AP 160000, Credit Bank 113100
  → Invoice cleared, PO marked Completed
  → P2P CYCLE COMPLETE! 🎉

---

## REPORTS AVAILABLE

Go to "Reports & Analytics" in sidebar:
  - MB52: Stock Overview (real-time stock quantities)
  - ME2L: PO by Vendor (total spend per vendor)
  - FBL1N: Vendor AP (open vs paid amounts)
  - Monthly Spend Summary

---

## PROJECT STRUCTURE

sap_p2p/
├── app.py              ← Main Python application (all backend logic)
├── requirements.txt    ← Python packages needed
├── sap_p2p.db          ← SQLite database (auto-created on first run)
├── README.md           ← This file
└── templates/          ← HTML pages
    ├── base.html           ← Main layout with navbar & sidebar
    ├── dashboard.html      ← Home screen with stats
    ├── materials.html      ← Material Master list
    ├── material_form.html  ← Create material
    ├── vendors.html        ← Vendor Master list
    ├── vendor_form.html    ← Create vendor
    ├── pr_list.html        ← Purchase Requisitions
    ├── pr_form.html        ← Create PR
    ├── rfq_list.html       ← RFQ list
    ├── rfq_form.html       ← Create RFQ
    ├── quotation_form.html ← Enter vendor quotes
    ├── rfq_compare.html    ← Price comparison (ME49)
    ├── po_list.html        ← Purchase Orders list
    ├── po_form.html        ← Create PO
    ├── po_view.html        ← PO detail view
    ├── gr_list.html        ← Goods Receipts list
    ├── gr_form.html        ← Post GR (MIGO)
    ├── invoice_list.html   ← Invoice list
    ├── invoice_form.html   ← Post Invoice (MIRO)
    ├── payment_list.html   ← Payment list
    ├── payment_form.html   ← Process payment
    └── reports.html        ← All reports

---

## TECHNOLOGIES USED

| Layer      | Technology              |
|------------|-------------------------|
| Backend    | Python 3.x + Flask      |
| Database   | SQLite (built into Python) |
| Frontend   | Bootstrap 5 + Bootstrap Icons |
| Templates  | Jinja2 (Flask templating) |
| Charts     | HTML tables             |

---

## TROUBLESHOOTING

Problem: "python not found"
Solution: Reinstall Python, check "Add to PATH" option

Problem: "ModuleNotFoundError: flask"
Solution: Run:  pip install flask

Problem: Port already in use
Solution: Change port at bottom of app.py:
  app.run(debug=True, port=5001)
  Then open: http://127.0.0.1:5001

Problem: Database errors / fresh start
Solution: Delete sap_p2p.db file and re-run app.py

---

## SAP TRANSACTION CODE MAPPING

| This App Screen    | SAP T-Code | Description                    |
|--------------------|------------|--------------------------------|
| Material Master    | MM01       | Create Material Master         |
| Vendor Master      | XK01       | Create Vendor Master           |
| Purchase Req.      | ME51N      | Create Purchase Requisition    |
| RFQ                | ME41       | Create Request for Quotation   |
| Quotation Entry    | ME47       | Maintain Quotation             |
| Price Comparison   | ME49       | Price Comparison List          |
| Purchase Order     | ME21N      | Create Purchase Order          |
| Goods Receipt      | MIGO       | Goods Movement (Mvt Type 101)  |
| Invoice Verify     | MIRO       | Enter Incoming Invoice         |
| Payment            | F110/F-53  | Payment Run / Manual Payment   |
| Stock Overview     | MB52       | Warehouse Stocks               |
| PO by Vendor       | ME2L       | Purchase Orders by Vendor      |
| Vendor AP          | FBL1N      | Vendor Line Item Display       |

---

KIIT University | SAP MM Capstone Project | April 2026
