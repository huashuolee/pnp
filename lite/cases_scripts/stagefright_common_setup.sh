#!/bin/bash

echo "************* ENABLE FPS LOG *****************"
echo "SET PROPERTY DEBUG.DUMP.LOG = 1"
adb wait-for-device
adb shell setprop debug.dump.log 1
sleep 2
level=`adb shell getprop debug.dump.log`
echo "GET PROPERTY DEBUG.DUMP.LOG = $level"
