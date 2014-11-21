#! /bin/bash
# Initialize the INV133600702  device

./dev/Merrifield.sh

echo "Initialize the INV131700489 device"

VALUE=56

adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='$VALUE' where name='screen_brightness';"

echo "replace the libs"
sleep 2
##adb push resource/libs/libs_inuse/ /system/lib/
#adb push resource/libs/libs_inuse/libstagefright.so /system/lib/
#adb push resource/libs/libs_inuse/libstagefright_foundation.so /system/lib/
#adb push resource/libs/libs_inuse/libstagefright_omx.so /system/lib/
#adb push resource/libs/libs_inuse/libmediaplayerservice.so /system/lib/

echo "Initialize the INV131700489 device done"
