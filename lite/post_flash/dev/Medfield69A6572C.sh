#! /bin/bash
# Initialize the  device


./dev/Baytrail.sh

echo "Initialize the Medfield69A6572C device baytrail"

VALUE=56
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='$VALUE' where name='screen_brightness';"

echo "Initialize the Medfield69A6572C device done"
