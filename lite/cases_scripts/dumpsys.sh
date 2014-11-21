#!/bin/bash

echo "[ Wait 8 seconds to start dumpsys ]"
sleep 8
echo "[ GET DUMPSYS SURFACEFLINGER $1 ]"
adb shell "mkdir /data/socwatch/dumpsys"
sleep 2
echo "dumpsys SurfaceFlinger > /data/socwatch/dumpsys/dumpsys_$1.txt &"
adb shell "dumpsys SurfaceFlinger > /data/socwatch/dumpsys/dumpsys_$1.txt &"
echo "[ GET DUMPSYS SURFACEFLINGER $1 DONE ]"
