echo "Initialize the Merrifield devices Common Settings"

# Init firsttime usage
adb shell "rm /system/app/SetupW*"
sleep 2
adb shell input tap 2400 1300
sleep 2
adb shell input tap 1280 1300
sleep 2
adb shell input tap 300 500
sleep 2
adb shell input keyevent 4
sleep 2

#remove nfc
adb shell "rm /system/app/Nfc*"
sleep 2
adb shell "rm -fr /data/data/com.android.nfc"
sleep 2

#Init system setting
echo "splite3 setting"
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update global set value='1' where name='airplane_mode_on';"
sleep 2
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='8' where name='volume_music';"
sleep 2
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='0' where name='screen_brightness_mode';"
sleep 2
adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update system set value='1800000' where name='screen_off_timeout';"
sleep 2
#adb shell sqlite3 /data/data/com.android.providers.settings/databases/settings.db "update secure set value='1' where name='lockscreen.disabled';"
adb shell sqlite3 /data/system/locksettings.db "update locksetting set `value`='1' where `name`='lockscreen.disabled';"
sleep 2

adb shell input keyevent 23
sleep 2
## SET THE SCREEN LOCK NONE
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
## SET THE SCREEN LOCK NONE END

#Init chrome

adb shell am start -a android.intent.action.VIEW -n com.android.chrome/.Main
sleep 5
adb shell input tap 1700 850 #No Thanks
sleep 1
adb shell input tap 1700 850
sleep 1
adb shell input tap 300 200  #chrome address bar
sleep 1
adb shell input keyevent 4
sleep 1
adb shell input keyevent 4
sleep 1
adb shell input keyevent 4
sleep 1

