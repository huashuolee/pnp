#!/bin/bash

echo "socwatch_sofia_v03/socwatch_sofia_android"
cd ../socwatch_sofia_v03/socwatch_sofia_android
./socwatch_android_install.sh
cd ../..
sleep 2
echo "adb push sh/MRFLD /data/socwatch"
adb push sh/MRFLD /data/socwatch
