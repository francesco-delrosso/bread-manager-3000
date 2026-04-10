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

#TODO: Fare una lista di tutte le piazzole e fare un controllo se l'utente ne inserisce una valida e per evitare confusioni bisogna controllare anche duplicati.

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'piccolo_camping_secret_2024')

# ── Configuration ────────────────────────────────────────────────────
DB_PATH          = os.path.join(os.path.dirname(__file__), 'orders.db')
MANAGER_PASSWORD = os.environ.get('MANAGER_PWD', 'camping2024')   # change this!
CUTOFF_HOUR      = 18   # prima delle 18:00 → domani disponibile; dopo → dopodomani

VALID_PITCHES = {str(i) for i in range(1, 61)} | {'5a', '12a', '33a', '59a'}

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

    name   = request.form.get('customer_name', '').strip()
    pitch  = request.form.get('pitch_number',  '').strip()
    ddates = request.form.getlist('delivery_dates')

    # Tieni solo le date valide al momento dell'invio
    valid = [d['value'] for d in get_available_dates(now)]
    ddates = [d for d in ddates if d in valid]

    if not name or not pitch or not ddates:
        return redirect(url_for('order_form'))
    if pitch.lower() not in VALID_PITCHES:
        return redirect(url_for('order_form'))

    quantities = {k: max(0, int(request.form.get(k, 0) or 0)) for k in PRICES}
    total = sum(quantities[k] * PRICES[k] for k in PRICES)

    if total == 0:
        return redirect(url_for('order_form'))

    with get_db() as conn:
        for ddate in ddates:
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
                            dates=','.join(ddates),
                            total=f"{total:.2f}"))

@app.route('/success')
def success():
    raw = request.args.get('dates', request.args.get('date', ''))
    dates = [d.strip() for d in raw.split(',') if d.strip()]
    return render_template('success.html',
                           name=request.args.get('name',''),
                           pitch=request.args.get('pitch',''),
                           dates=dates,
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

    with get_db() as conn:
        dates = conn.execute(
            'SELECT DISTINCT delivery_date FROM orders ORDER BY delivery_date DESC'
        ).fetchall()

        # Se non c'è ?date= nell'URL usa la prima data con ordini,
        # altrimenti cade su oggi (DB vuoto).
        sel = request.args.get('date') or (dates[0]['delivery_date'] if dates else today)

        orders = conn.execute(
            'SELECT * FROM orders WHERE delivery_date=? ORDER BY created_at',
            (sel,)).fetchall()

    # totals per product
    totals = {k: sum(o[k] for o in orders) for k in PRICES}
    grand  = sum(o['total_amount'] for o in orders)

    return render_template('manager.html',
                           orders=orders, dates=dates,
                           selected_date=sel,
                           totals=totals,
                           grand_total=grand,
                           prices=PRICES,
                           available_dates=get_available_dates(datetime.now()))

@app.route('/manager/stats')
def manager_stats():
    if not session.get('mgr'):
        return redirect(url_for('manager_login'))

    with get_db() as conn:
        # Totali generali
        overview = conn.execute('''
            SELECT COUNT(*)                       AS n_orders,
                   COALESCE(SUM(total_amount), 0) AS revenue,
                   COUNT(DISTINCT delivery_date)  AS n_days
            FROM orders
        ''').fetchone()

        # Quantità per prodotto
        prod = conn.execute('''
            SELECT COALESCE(SUM(francesino),0),
                   COALESCE(SUM(grano_duro),0),
                   COALESCE(SUM(multicereale),0),
                   COALESCE(SUM(cornetto_vuoto),0),
                   COALESCE(SUM(cornetto_marmellata),0),
                   COALESCE(SUM(cornetto_cioccolato),0),
                   COALESCE(SUM(cornetto_crema),0)
            FROM orders
        ''').fetchone()

        # Riepilogo settimanale (ultime 8 settimane)
        weeks = conn.execute('''
            SELECT strftime('%Y', delivery_date) || ' – Sett. ' ||
                   CAST(strftime('%W', delivery_date) AS INTEGER) AS week,
                   COUNT(*)            AS n_orders,
                   SUM(total_amount)   AS revenue
            FROM orders
            GROUP BY strftime('%Y%W', delivery_date)
            ORDER BY delivery_date DESC
            LIMIT 8
        ''').fetchall()

        # Riepilogo per giorno (ultimi 30 giorni con ordini)
        days = conn.execute('''
            SELECT delivery_date,
                   COUNT(*)          AS n_orders,
                   SUM(total_amount) AS revenue
            FROM orders
            GROUP BY delivery_date
            ORDER BY delivery_date DESC
            LIMIT 30
        ''').fetchall()

    PROD_LABELS = [
        ('francesino',          '🍞 Francesino'),
        ('grano_duro',          '🌾 Grano duro'),
        ('multicereale',        '🌱 Multicereale'),
        ('cornetto_vuoto',      '🥐 Cornetto vuoto'),
        ('cornetto_marmellata', '🍓 Cornetto marmellata'),
        ('cornetto_cioccolato', '🍫 Cornetto cioccolato'),
        ('cornetto_crema',      '🍮 Cornetto crema'),
    ]
    prod_totals = [(label, prod[i]) for i, (_, label) in enumerate(PROD_LABELS)]
    prod_totals_named = list(zip([k for k, _ in PROD_LABELS], prod_totals))
    # lista (chiave, etichetta, quantità) ordinata per quantità desc
    ranking = sorted(
        [(k, label, prod[i]) for i, (k, label) in enumerate(PROD_LABELS)],
        key=lambda x: x[2], reverse=True
    )
    max_qty = ranking[0][2] if ranking and ranking[0][2] > 0 else 1

    n_days = overview['n_days'] or 1  # evita divisione per zero
    return render_template('stats.html',
                           n_orders=overview['n_orders'],
                           revenue=overview['revenue'],
                           n_days=overview['n_days'],
                           avg_revenue=overview['revenue'] / n_days,
                           avg_orders=overview['n_orders'] / n_days,
                           ranking=ranking,
                           max_qty=max_qty,
                           weeks=weeks,
                           days=days)

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

@app.route('/manager/cornetti')
def manager_cornetti():
    if not session.get('mgr'):
        return redirect(url_for('manager_login'))

    today = datetime.now().strftime('%Y-%m-%d')

    with get_db() as conn:
        dates = conn.execute(
            'SELECT DISTINCT delivery_date FROM orders ORDER BY delivery_date DESC'
        ).fetchall()

        sel = request.args.get('date') or (dates[0]['delivery_date'] if dates else today)

        orders = conn.execute(
            'SELECT * FROM orders WHERE delivery_date=? ORDER BY created_at',
            (sel,)).fetchall()

    cornetti_keys = ['cornetto_vuoto', 'cornetto_marmellata', 'cornetto_cioccolato', 'cornetto_crema']
    totals = {k: sum(o[k] for o in orders) for k in cornetti_keys}
    grand  = sum(totals.values())

    return render_template('cornetti.html',
                           orders=orders, dates=dates,
                           selected_date=sel,
                           totals=totals,
                           grand_total=grand)

@app.route('/manager/new-order', methods=['POST'])
def manager_new_order():
    if not session.get('mgr'):
        return redirect(url_for('manager_login'))

    name  = request.form.get('customer_name', '').strip()
    pitch = request.form.get('pitch_number',  '').strip()
    date  = request.form.get('delivery_date', '').strip()

    if not name or not pitch or not date:
        return redirect(url_for('manager_dashboard'))

    quantities = {k: max(0, int(request.form.get(k, 0) or 0)) for k in PRICES}
    total = sum(quantities[k] * PRICES[k] for k in PRICES)

    if total == 0:
        return redirect(url_for('manager_dashboard', date=date))

    with get_db() as conn:
        conn.execute('''INSERT INTO orders
            (delivery_date, customer_name, pitch_number,
             francesino, grano_duro, multicereale,
             cornetto_vuoto, cornetto_marmellata,
             cornetto_cioccolato, cornetto_crema, total_amount)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (date, name, pitch,
             quantities['francesino'],      quantities['grano_duro'],
             quantities['multicereale'],    quantities['cornetto_vuoto'],
             quantities['cornetto_marmellata'], quantities['cornetto_cioccolato'],
             quantities['cornetto_crema'],  total))

    return redirect(url_for('manager_dashboard', date=date))

@app.route('/manager/edit/<int:order_id>', methods=['POST'])
def manager_edit(order_id):
    if not session.get('mgr'):
        return redirect(url_for('manager_login'))
    date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
    quantities = {k: max(0, int(request.form.get(k, 0) or 0)) for k in PRICES}
    total = sum(quantities[k] * PRICES[k] for k in PRICES)
    with get_db() as conn:
        conn.execute('''UPDATE orders SET
            francesino=?, grano_duro=?, multicereale=?,
            cornetto_vuoto=?, cornetto_marmellata=?,
            cornetto_cioccolato=?, cornetto_crema=?,
            total_amount=?
            WHERE id=?''',
            (quantities['francesino'],      quantities['grano_duro'],
             quantities['multicereale'],    quantities['cornetto_vuoto'],
             quantities['cornetto_marmellata'], quantities['cornetto_cioccolato'],
             quantities['cornetto_crema'],  total, order_id))
    return redirect(url_for('manager_dashboard', date=date))

@app.route('/manager/delete/<int:order_id>', methods=['POST'])
def manager_delete(order_id):
    if not session.get('mgr'):
        return redirect(url_for('manager_login'))
    with get_db() as conn:
        conn.execute('DELETE FROM orders WHERE id = ?', (order_id,))
    return redirect(url_for('manager_dashboard'))

@app.route('/manager/poll')
def manager_poll():
    if not session.get('mgr'):
        return {'error': 'unauthorized'}, 401
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    with get_db() as conn:
        count = conn.execute(
            'SELECT COUNT(*) FROM orders WHERE delivery_date=?', (date,)
        ).fetchone()[0]
    return {'count': count}

@app.route('/manager/logout')
def manager_logout():
    session.pop('mgr', None)
    return redirect(url_for('manager_login'))

# ── Seed ─────────────────────────────────────────────────────────────
def seed_db():
    """Inserisce ordini di prova solo se il database è vuoto."""
    with get_db() as conn:
        if conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0] > 0:
            return  # dati già presenti, non sovrascrivere

        now = datetime.now()
        d1  = (now + timedelta(days=1)).strftime('%Y-%m-%d')  # domani
        d2  = (now + timedelta(days=2)).strftime('%Y-%m-%d')  # dopodomani
        d3  = (now + timedelta(days=3)).strftime('%Y-%m-%d')  # +3 giorni

        INSERT = '''INSERT INTO orders
            (delivery_date, customer_name, pitch_number,
             francesino, grano_duro, multicereale,
             cornetto_vuoto, cornetto_marmellata,
             cornetto_cioccolato, cornetto_crema, total_amount)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)'''

        sample = [
            # (data, cognome, piazzola, fra, gd, mul, c_vuo, c_mar, c_cio, c_cre)
            (d1, 'Müller',     '12',  2, 1, 0, 2, 0, 1, 0),
            (d1, 'Schneider',  '7',   0, 0, 1, 0, 2, 0, 2),
            (d1, 'Fischer',    '23',  3, 0, 0, 1, 1, 0, 0),
            (d1, 'Weber',      '5',   1, 2, 0, 0, 0, 2, 1),
            (d2, 'Bauer',      '18',  2, 0, 1, 3, 0, 0, 1),
            (d2, 'Koch',       '3',   0, 1, 0, 0, 1, 1, 0),
            (d2, 'Hoffmann',   '31',  4, 0, 0, 2, 2, 0, 0),
            (d3, 'Schäfer',    '9',   1, 1, 1, 0, 0, 0, 3),
            (d3, 'Zimmermann', '14',  0, 0, 2, 1, 0, 1, 1),
        ]

        for row in sample:
            d, nome, piaz, fra, gd, mul, cvu, cma, cch, ccr = row
            total = (fra*0.70 + gd*0.80 + mul*2.70 +
                     cvu*1.60 + cma*1.60 + cch*1.60 + ccr*1.60)
            conn.execute(INSERT, (d, nome, piaz, fra, gd, mul, cvu, cma, cch, ccr, total))

# ── Run ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    seed_db()
    app.run(debug=False, host='0.0.0.0', port=8000)
