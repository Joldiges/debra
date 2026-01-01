#!/bin/bash

# rsync a backup but use excludes from excludes.txt which is in the same folder

EXCLUDES_FILE="$(dirname "$0")/excludes.txt"
SOURCE="/"
DESTINATION="/mnt/backup/"
RSYNC_OPTIONS="-aAXv --delete"
RSYNC_EXCLUDES=""
while IFS= read -r line; do
    RSYNC_EXCLUDES+="--exclude=\"$line\" "
done < "$EXCLUDES_FILE"
RSYNC_COMMAND="sudo rsync $RSYNC_OPTIONS $RSYNC_EXCLUDES \"$DESTINATION\" \"$SOURCE\""
eval "$RSYNC_COMMAND"
echo "Backup completed successfully."
