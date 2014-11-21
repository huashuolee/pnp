#!/bin/bash

function get_mediainfo(){
    path=$1
    if [ $# == 0 ]; then
        base_dir="./"
    else
        base_dir=$path
    fi

    for x in `ls $base_dir | grep mp4`
    do
        echo "file={$x}"
        mediainfo $base_dir/$x > $base_dir/mediainfo_mp4_record
    done
}


path=$1

if [ -z $path ]; then
echo "please give a path"
exit
fi


echo "[##### SOCWATCH DATA PULL FROM DEVICE #####]"
adb pull /data/socwatch/results $path
adb pull /sdcard/DCIM/100ANDRO $path
adb pull /data/socwatch/dumpsys $path
adb shell rm /sdcard/DCIM/100ANDRO/*
sleep 2
#cd test_case
#mkdir log
#mv *_rcc_* log
#mv fps* log
#mv os_version log  #create in pmbot.py
#cd -
#mv test_case/log $path
#adb shell "rm -rf /data/socwatch/results/"
#adb shell "rm -rf /data/socwatch/dumpsys/"
sleep 2

echo "create mediainfo file"
get_mediainfo $path
