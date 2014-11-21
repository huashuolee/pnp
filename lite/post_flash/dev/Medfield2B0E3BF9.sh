#! /bin/bash
# Initialize the Medfield2B0E3BF9 device

./dev/Merrifield.sh

echo "Initialize the Medfield2B0E3BF9 device"

VALUE=55
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='$VALUE' where name='screen_brightness';"

./dev/vvboard.sh

echo "replace the libs"
sleep 2
#adb push resource/libs/libs_inuse /system/lib/

echo "Initialize the Medfield2B0E3BF9 device done"
