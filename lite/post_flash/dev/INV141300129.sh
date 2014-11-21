#! /bin/bash
# Initialize the INV140400609 device

./dev/Merrifield.sh

echo "Initialize the INV140400609 device"

VALUE=60

adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='$VALUE' where name='screen_brightness';"
echo "Execution result:"$?
echo "Initialize the INV140400609 device done"
