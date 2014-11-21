#! /bin/bash
# Initialize the BayTrailTee86d4a1 device

./dev/Baytrail.sh


VALUE=224
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='$VALUE' where name='screen_brightness';"


echo "Initialize the BayTrailTee86d4a1 device done"
