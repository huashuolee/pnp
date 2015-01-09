#! /bin/bash
# Initialize the Sofia0123456789ABCDEF device

./dev/Merrifield.sh
#./Merrifield.sh

echo "Initialize the Sofia0123456789ABCDEF device"

#six 
#VALUE=53

#seven
#VALUE=60
#MRD5S
#VALUE= 40 
#sevenP1
VALUE=44

adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='$VALUE' where name='screen_brightness';"
sleep 2
echo "DISABLE AUTOROTATION"
#adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='0' where name='accelerometer_rotation'";
sleep 2
#adb shell content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:1
sleep 3
echo "Execution result:"$?
#adb reboot
sleep 2
#adb install Chrome_M32_Stable/Chrome_M32_Stable_32.0.1700.99_x86.apk
#sleep 10
#adb push resource/mp4/BBB_1080p_12Mbps_audio_44100_30fps_HP.mp4 /sdcard/
#sleep 190
echo "Initialize the Sofia0123456789ABCDEF device done"
