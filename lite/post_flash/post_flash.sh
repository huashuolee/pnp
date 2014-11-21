#!/bin/bash
function Usage() {
    echo "[Usage]"
    echo -e "\t$0 platform[MRFLD | BYT]"
    echo "[Example] $0 MRFLD"
    echo "[Example] $0 BYT"
}

function check_target()
{
    target="$1";
    target_test=`adb shell ls $target`;
    if [[ ! $target_test == *"No such file or directory"* ]]; then
        echo "1";
    else
        echo "0";
    fi
}

function dev_replace_apk()
{
    echo "replace the Gallery2.apk "
    sleep 2
    mkdir APK_BAK
    adb pull /system/apks/Gallery2.apk ./APK_BAK/
    echo  "BACK UP apks to APK_BAK"
    adb shell rm /system/app/Gallery2.*
    sleep 2
    adb push resource/apks/Gallery2.apk /system/app
}

function dev_install_socwatch()
{
    echo "socwatch_sofia_v03/socwatch_sofia_android"
    cd socwatch_sofia_v03/socwatch_sofia_android
    ./socwatch_android_install.sh
    cd ../..
    sleep 2
    if [ "$1" == "BYT" ]; then
        echo "adb push sh/BYT /data/socwatch"
        adb push sh/BYT /data/socwatch
    elif [ "$1" == "MRFLD" ]; then
        echo "adb push sh/MRFLD /data/socwatch"
         #adb push sh/MRFLD/socwatch_on_dev.sh /data/socwatch
         #adb push sh/MRFLD/init.sh /data/socwatch
         #adb push sh/MRFLD/usermode.sh /data/socwatch
        adb push sh/MRFLD /data/socwatch
    fi

}

function dev_install_powertop()
{
    echo "install powertop"
    #adb shell mkdir /data/powertop/
    sleep 2
    cd powertop13
    adb push powertop /data/socwatch/
    #adb push powertop.sh /data/socwatch/
    sleep 5
    cd ..
}
function push_media_file()
    for item in `cat ./resource/sofia_media.list`
    do 
       echo "Push $item"
       adb push $item /sdcard/
    done
function dev_push_media_file_via_cases()
{
#    media_files=`cat test_cases.conf | grep '^[^#]' | sed 's/^.*://g'`
     media_files=`cat test_cases.conf | grep '^[^#]' | awk -F':' '{printf("%s\n",$7)}'`
    for media_file in $media_files
    do
        echo "media_file = {$media_file}"
        check_ret=$(check_target /sdcard/$media_file)
        if [ "$check_ret" == "0" ]; then
            echo "Push file $media_file to Android device"
            echo "adb push resource/mp4/$media_file /sdcard/"
            adb push resource/mp4/$media_file /sdcard/
        else
            echo "[FILE EXIST] $media_file"
        fi
    done
}

function dev_push_media_files()
{
    target_file="/sdcard/big_buck_bunny_1080p_audio_30fps.mp4"
    check_ret=$(check_target $target_file)
    sleep 2
    echo
    echo "CHECK_TARGET $check_ret ##"
    echo
    if [ "$check_ret" == "0" ]; then
        echo "push mp4 file to $SERIAL device sdcard"
        sleep 2
#       adb push resource/mp4/ /sdcard/

#       adb push resource/mp4/bbb_1080p_c_elecard_4tiles-h265-24fps.mp4 /sdcard/
#       echo "bbb_1080p_c_elecard_4tiles-h264-24fps.mp4 pushed"
#       adb push resource/mp4/bbb_720p_c_elecard_4tiles.h265.24fps.mp4 /sdcard/
#       echo "bbb_720p_c_elecard_4tiles-h264-24fps.mp4 pushed"

#        adb push resource/mp4/big_buck_bunny_1080p_audio_30fps.mp4 /sdcard/
#        echo "big_buck_bunny_1080p_audio_30fps.mp4 pushed"
        adb push resource/mp4/BBB_1080p_12Mbps_audio_44100_30fps_HP.mp4 /sdcard/
        echo "BBB_1080p_12Mbps_audio_44100_30fps_HP.mp4 pushed"
#        adb push resource/mp4/big_buck_bunny_1080p_audio_60fps_3min.mp4 /sdcard/
#        echo "BBB_1080p_12Mbps_audio_44100_30fps_HP.mp4 pushed"
#        adb push resource/mp4/big_buck_bunny_720p_audio_60fps_3min.mp4 /sdcard/
#        echo "big_buck_bunny_720p_audio_60fps_3min.mp4 pushed"
#        echo "MP4 file pushed"
    fi

#       adb push resource/mp4/big_buck_bunny_1080p_audio_30fps.mp4 /sdcard/
}

function dev_connect()
{
    echo "wait for devices online"
    adb wait-for-device
    echo "devices is online"
    echo "wait 5 seconds"
    sleep 5
    adb root
#    sleep 5
    adb wait-for-device
    adb remount
#   sleep 2
    adb wait-for-device
}

function rm_setup()
{
    adb shell rm /system/priv-app/SetupW*
}

function dev_init()
{
    #SERIAL=`adb get-serialno`
    echo "initialize the device"
    #adb shell "input keyevent 26"
    #sleep 2
    #adb shell "input keyevent 26"
    #sleep 2
    sh dev_init.sh
}

function dev_reboot()
{
    echo "The System is going to be rebooting..."
    sleep 2
    adb reboot
}



####################################
####################################
#Syntax check
if [ $# != 1 ]; then
Usage
exit
fi

CURDIR=`pwd`
echo "Post flash, current dir: "
echo $CURDIR

dev_connect
dev_init
rm_setup
dev_install_socwatch $1
dev_install_powertop
#dev_replace_apk

#dev_push_media_files
#dev_push_media_file_via_cases
push_media_file
dev_reboot

echo "All done."
exit 0

