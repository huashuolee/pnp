echo "Initialize the Merrifield devices Common Settings"

# Init firsttime usage
#adb shell "rm /system/app/SetupW*"  remove SetupWizard
adb root
adb wait-for-device root
#sleep 2
adb wait-for-device remount
#sleep 2
adb wait-for-device

#files="adb shell find / -name SetupWizard*"
#
#for file in `$files`
#do
#echo "remove file: "$file
#adb shell rm $(echo "$file" | tr -d '\r')
#sleep 1
#done
#adb shell "rm /system/priv-app/SetupW*"  remove SetupWizard
#adb shell "rm /system/priv-app/SetupW*"

#adb shell input keyevent 66
#adb shell input keyevent 66

#sleep 2
#adb shell input tap 360 1150
#sleep 2
#adb shell input tap 660 1150
#sleep 2
#adb shell input keyevent 4
#sleep 2

### If remove the NFC, the com.android.settings can not be lunched on Saltbay-Pr2 since build ww47 Android 4.4
##remove nfc
#adb shell "rm /system/app/Nfc*"
#sleep 2
#adb shell "rm -fr /data/data/com.android.nfc"
#sleep 2

#Init system setting
echo "splite3 setting"
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update global set value='1' where name='airplane_mode_on';"
sleep 2
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='7' where name='volume_music';"
sleep 2
#adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='5' where name='volume_ring';"
#sleep 2
#adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='7' where name='volume_system';"
#sleep 2
#adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='4' where name='volume_voice';"
#sleep 2
#adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='6' where name='volume_alarm';"
#sleep 2
#adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='5' where name='volume_notification';"
#sleep 2
#adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='7' where name='volume_bluetooth_sco';"
#sleep 2
#adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='2' where name='volume_fm';"
#sleep 2
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='0' where name='screen_brightness_mode';"
sleep 2
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='1800000' where name='screen_off_timeout';"
sleep 2
#adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update secure set value='1' where name='lockscreen.disabled';"
adb shell sqlite3 /data/system/locksettings.db "update locksettings set value='1' where name='lockscreen.disabled';"
sleep 2

#adb shell input keyevent 23
#sleep 2
# SET THE SCREEN LOCK NONE
#adb shell am start -a android.settings.SECURITY_SETTINGS
#sleep 2
#adb shell input keyevent 20  #send keyevent "KEYCODE_DPAD_DOWN"
#sleep 1
#adb shell input keyevent 23  #send keyevent "KEYCODE_DPAD_CENTER"
#sleep 1
#adb shell input keyevent 23  #send keyevent "KEYCODE_DPAD_CENTER"
#sleep 2
#adb shell input keyevent 4   #send keyevent "KEYCODE_BACK"
#sleep 2
#adb shell input keyevent 4   #send keyevent "KEYCODE_BACK"
#sleep 2
#adb shell input keyevent 3   #send keyevent "KEYCODE_HOME"
# SET THE SCREEN LOCK NONE END

#Init chrome
#adb shell input keyevent 66
#adb shell input keyevent 66
#
#adb shell am start -a android.intent.action.VIEW -n com.android.chrome/.Main
#sleep 5
#adb shell input tap 360 1100
#sleep 1
#adb shell input tap 360 1120
#sleep 1
#adb shell input tap 60 90
#sleep 1
#adb shell input keyevent 4
#sleep 1
#adb shell input keyevent 4
#sleep 1
#adb shell input keyevent 4
#sleep 1
#
#adb shell input keyevent 66
#adb shell input keyevent 66
