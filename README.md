# Piccolo Camping – Sistema Ordini Pane e Dolci

App web mobile-friendly per ordinare pane e cornetti freschi.
3 lingue: 🇩🇪 Tedesco (principale) · 🇮🇹 Italiano · 🇬🇧 Inglese

---

## Come funziona

| Chi | Cosa fa |
|-----|---------|
| **Cliente** | Scansiona il QR code → compila il modulo su smartphone → invia entro le 18:00 |
| **Gestore** | Accede a `/manager` con password → vede tutti gli ordini del giorno → stampa o scarica CSV |

---

## Installazione (5 minuti)

### Requisiti
- Python 3.9+ (già presente su quasi tutti i server Linux/Mac)
- Connessione Internet per la prima installazione

### Passaggi

```bash
# 1. Entra nella cartella
cd piccolo-camping-ordini

# 2. Installa le dipendenze
pip install -r requirements.txt

# 3. (Opzionale) Cambia la password del gestore nel file app.py
#    cerca la riga:  MANAGER_PASSWORD = os.environ.get('MANAGER_PWD', 'camping2024')
#    e sostituisci 'camping2024' con la tua password

# 4. Avvia l'app
python app.py
```

L'app sarà disponibile su `http://TUO-IP:5000`

### Per uso in produzione (server Linux)
```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:80 app:app
```

---

## Generare il QR code

```bash
# Sostituisci con l'URL reale del tuo server
python generate_qr.py http://TUO-DOMINIO.com
```

Il file `qrcode_ordini.png` può essere inserito nella locandina o stampato.

---

## Pagine disponibili

| URL | Descrizione |
|-----|-------------|
| `/` | Modulo ordine cliente (mobile) |
| `/success` | Conferma ordine |
| `/manager` | Login gestore |
| `/manager/dashboard` | Dashboard ordini con totali |
| `/manager/export?date=AAAA-MM-GG` | Scarica CSV del giorno |

---

## Configurazione

Nel file `app.py` puoi modificare:
```python
MANAGER_PASSWORD = 'camping2024'   # ← cambia questa!
CUTOFF_HOUR      = 18              # orario limite ordini
```

---

## File inclusi

```
piccolo-camping-ordini/
├── app.py                  ← Backend Flask
├── requirements.txt        ← Dipendenze Python
├── generate_qr.py          ← Generatore QR code
├── orders.db               ← Database SQLite (creato automaticamente)
├── qrcode_ordini.png       ← QR code generato
└── templates/
    ├── order.html          ← Modulo cliente (trilingue, mobile)
    ├── success.html        ← Conferma ordine
    ├── manager_login.html  ← Login gestore
    └── manager.html        ← Dashboard ordini
```
