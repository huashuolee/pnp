#! /bin/bash
# Initialize the Medfield3C1D2C74 device

./dev/Merrifield.sh

echo "Initialize the Medfield3C1D2C74 device"

VALUE=55
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='$VALUE' where name='screen_brightness';"

./dev/vvboard.sh

echo "replace the libs"
sleep 2
adb push resource/libs/libs_inuse /system/lib/

echo "Initialize the Medfield3C1D2C74 device done"
