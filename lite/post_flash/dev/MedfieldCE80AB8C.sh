#! /bin/bash
# Initialize the INV131700489  device

./dev/Merrifield.sh

echo "Initialize the INV131700489 device"

VALUE=56

adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='$VALUE' where name='screen_brightness';"

echo "Initialize the INV131700489 device done"
