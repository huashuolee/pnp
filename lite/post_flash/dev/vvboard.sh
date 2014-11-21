#! /bin/bash
## works need to be done on VVBOARD only

#install apk to do rotation (to landscape)
adb root
adb wait-for-device

echo "adb install /SPMaccelerometerControl.apk"
adb install resource/apks/SPMaccelerometerControl.apk
echo "rotate to landscape"
adb shell << EOF
am start -a android.intent.action.MAIN -n com.intel.spm.accelerometercontrol/.SPMrotationActivity --es accelerometer 0 --es user_rotation 1
exit
EOF

