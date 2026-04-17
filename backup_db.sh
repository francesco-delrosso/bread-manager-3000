#!/bin/bash
# Backup orders.db su chiavetta USB con timestamp
# Uso: ./backup_db.sh
# Crontab (ogni ora): 0 * * * * /home/pi/piccolo-camping-ordini/backup_db.sh
#
# Prerequisiti:
#   - Chiavetta USB montata su /mnt/usb (vedi /etc/fstab)
#   - mkdir -p /mnt/usb/backups

DB_SOURCE="${DB_PATH:-/mnt/usb/orders.db}"
BACKUP_DIR="/mnt/usb/backups"
MAX_BACKUPS=168  # 7 giorni * 24 ore

# Verifica che la USB sia montata
if ! mountpoint -q /mnt/usb; then
    echo "ERRORE: /mnt/usb non montata" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/orders_${TIMESTAMP}.db"

# Usa sqlite3 .backup per copia consistente (non cp!)
sqlite3 "$DB_SOURCE" ".backup '$BACKUP_FILE'"

if [ $? -eq 0 ]; then
    echo "Backup OK: $BACKUP_FILE"
else
    echo "ERRORE backup fallito" >&2
    exit 1
fi

# Rimuovi backup vecchi (tiene ultimi MAX_BACKUPS)
cd "$BACKUP_DIR" && ls -t orders_*.db 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm --
