#!/bin/bash
case_name=$1

echo "GET FPS ------> fps_$case_name"

adb logcat -c
sleep 2
adb logcat -v time > fps_$case_name &

echo "GET FPS ------> fps_$case_name DONE"


