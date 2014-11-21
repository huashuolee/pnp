#!/bin/bash 
adb root
sleep 2
adb remount
sleep 2

files="adb shell find / -name SetupWizard*"

for file in `$files`
do
echo "remove file: "$file
adb shell rm $(echo "$file" | tr -d '\r')
sleep 1
done
