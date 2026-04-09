"""
Piccolo Camping – Sistema Ordini Pane e Dolci
Flask + SQLite | DE / IT / EN
"""
from flask import (Flask, render_template, request,
                   redirect, url_for, session, make_response)
import sqlite3
import csv
import io
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'piccolo_camping_secret_2024')

# ── Configuration ────────────────────────────────────────────────────
DB_PATH          = os.path.join(os.path.dirname(__file__), 'orders.db')
MANAGER_PASSWORD = os.environ.get('MANAGER_PWD', 'camping2024')   # change this!
CUTOFF_HOUR      = 18   # prima delle 18:00 → domani disponibile; dopo → dopodomani

PRICES = {
    'francesino':           0.70,
    'grano_duro':           0.80,
    'multicereale':         2.70,
    'cornetto_vuoto':       1.60,
    'cornetto_marmellata':  1.60,
    'cornetto_cioccolato':  1.60,
    'cornetto_crema':       1.60,
}

DAYS_DE = ['Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag']
DAYS_IT = ['Lunedì','Martedì','Mercoledì','Giovedì','Venerdì','Sabato','Domenica']
DAYS_EN = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

# ── Database ─────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS orders (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at          TEXT    DEFAULT (datetime('now','localtime')),
            delivery_date       TEXT    NOT NULL,
            customer_name       TEXT    NOT NULL,
            pitch_number        TEXT    NOT NULL,
            francesino          INTEGER DEFAULT 0,
            grano_duro          INTEGER DEFAULT 0,
            multicereale        INTEGER DEFAULT 0,
            cornetto_vuoto      INTEGER DEFAULT 0,
            cornetto_marmellata INTEGER DEFAULT 0,
            cornetto_cioccolato INTEGER DEFAULT 0,
            cornetto_crema      INTEGER DEFAULT 0,
            total_amount        REAL    DEFAULT 0
        )''')

# ── Helpers ───────────────────────────────────────────────────────────
def is_past_cutoff(now: datetime) -> bool:
    return now.hour >= CUTOFF_HOUR

def get_available_dates(now: datetime) -> list:
    """Genera i prossimi 7 giorni consegnabili.

    Prima delle 18:00 la prima data disponibile è domani (delta=1).
    Dopo le 18:00 la prima data disponibile è dopodomani (delta=2).
    """
    start = 2 if is_past_cutoff(now) else 1
    dates = []
    for idx, delta in enumerate(range(start, start + 7)):
        d   = (now + timedelta(days=delta)).date()
        fmt = d.strftime('%d.%m.%Y')
        wd  = d.weekday()   # 0=Lun … 6=Dom
        if idx == 0 and delta == 1:
            de = f'Morgen, {fmt}'
            it = f'Domani, {fmt}'
            en = f'Tomorrow, {fmt}'
        elif idx == 0 and delta == 2:
            de = f'Übermorgen, {fmt}'
            it = f'Dopodomani, {fmt}'
            en = f'Day after tomorrow, {fmt}'
        else:
            de = f'{DAYS_DE[wd]}, {fmt}'
            it = f'{DAYS_IT[wd]}, {fmt}'
            en = f'{DAYS_EN[wd]}, {fmt}'
        dates.append({'value': d.strftime('%Y-%m-%d'), 'de': de, 'it': it, 'en': en})
    return dates

# ── Customer routes ───────────────────────────────────────────────────
@app.route('/')
def order_form():
    now = datetime.now()
    return render_template('order.html',
                           available_dates=get_available_dates(now),
                           prices=PRICES)

@app.route('/submit', methods=['POST'])
def submit_order():
    now = datetime.now()

    name  = request.form.get('customer_name', '').strip()
    pitch = request.form.get('pitch_number',  '').strip()
    ddate = request.form.get('delivery_date', '').strip()

    # Validazione server-side: la data deve essere tra quelle attualmente valide
    valid_dates = [d['value'] for d in get_available_dates(now)]
    if not name or not pitch or ddate not in valid_dates:
        return redirect(url_for('order_form'))

    quantities = {k: max(0, int(request.form.get(k, 0) or 0)) for k in PRICES}
    total = sum(quantities[k] * PRICES[k] for k in PRICES)

    if total == 0:
        return redirect(url_for('order_form'))

    with get_db() as conn:
        conn.execute('''INSERT INTO orders
            (delivery_date, customer_name, pitch_number,
             francesino, grano_duro, multicereale,
             cornetto_vuoto, cornetto_marmellata,
             cornetto_cioccolato, cornetto_crema, total_amount)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (ddate, name, pitch,
             quantities['francesino'],      quantities['grano_duro'],
             quantities['multicereale'],    quantities['cornetto_vuoto'],
             quantities['cornetto_marmellata'], quantities['cornetto_cioccolato'],
             quantities['cornetto_crema'],  total))

    return redirect(url_for('success',
                            name=name, pitch=pitch,
                            date=ddate, total=f"{total:.2f}"))

@app.route('/success')
def success():
    return render_template('success.html',
                           name=request.args.get('name',''),
                           pitch=request.args.get('pitch',''),
                           date=request.args.get('date',''),
                           total=request.args.get('total','0.00'))

# ── Manager routes ────────────────────────────────────────────────────
@app.route('/manager', methods=['GET', 'POST'])
def manager_login():
    error = False
    if request.method == 'POST':
        if request.form.get('password') == MANAGER_PASSWORD:
            session['mgr'] = True
            return redirect(url_for('manager_dashboard'))
        error = True
    return render_template('manager_login.html', error=error)

@app.route('/manager/dashboard')
def manager_dashboard():
    if not session.get('mgr'):
        return redirect(url_for('manager_login'))

    today = datetime.now().strftime('%Y-%m-%d')
    sel   = request.args.get('date', today)

    with get_db() as conn:
        orders = conn.execute(
            'SELECT * FROM orders WHERE delivery_date=? ORDER BY created_at',
            (sel,)).fetchall()
        dates = conn.execute(
            'SELECT DISTINCT delivery_date FROM orders ORDER BY delivery_date DESC'
        ).fetchall()

    # totals per product
    totals = {k: sum(o[k] for o in orders) for k in PRICES}
    grand  = sum(o['total_amount'] for o in orders)

    return render_template('manager.html',
                           orders=orders, dates=dates,
                           selected_date=sel,
                           totals=totals,
                           grand_total=grand,
                           prices=PRICES)

@app.route('/manager/export')
def manager_export():
    if not session.get('mgr'):
        return redirect(url_for('manager_login'))

    sel = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    with get_db() as conn:
        orders = conn.execute(
            'SELECT * FROM orders WHERE delivery_date=? ORDER BY created_at',
            (sel,)).fetchall()

    si  = io.StringIO()
    cw  = csv.writer(si, delimiter=';')
    cw.writerow(['ID','Ora ordine','Data consegna','Cognome','Piazzola',
                 'Francesino','Grano Duro','Multicereale',
                 'Cornetto vuoto','Cornetto marmellata',
                 'Cornetto cioccolato','Cornetto crema','Totale €'])
    for o in orders:
        cw.writerow([o['id'], o['created_at'], o['delivery_date'],
                     o['customer_name'], o['pitch_number'],
                     o['francesino'], o['grano_duro'], o['multicereale'],
                     o['cornetto_vuoto'], o['cornetto_marmellata'],
                     o['cornetto_cioccolato'], o['cornetto_crema'],
                     f"{o['total_amount']:.2f}"])

    resp = make_response(si.getvalue())
    resp.headers['Content-Disposition'] = f'attachment; filename=ordini_{sel}.csv'
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    return resp

@app.route('/manager/logout')
def manager_logout():
    session.pop('mgr', None)
    return redirect(url_for('manager_login'))

# ── Run ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=8000)
