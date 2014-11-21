#!/bin/bash
#  ***************************************************************************************
#  Copyright 2014 Intel Corporation. All rights reserved.
#  Other names and brands may be claimed sa the property of others.
#  Internal use only -- Do Not Distribute
#  ***************************************************************************************
#
# A rudimentary script to copy the driver
# and support files to the Android
# target data.

# Set adb device number
ADB="adb"
BASE_DIR="/data"
DRIVER_MAJOR=1
DRIVER_MINOR=2

usage()
{
	echo ""
    echo "Usage: ./socwatch_android_install <options>";
    echo "Where options are:";
	echo "";
    echo "  -s [device name]: specify a device name e.g. \"Medfield1234\".";
    echo "  	Use this option if you typically have more than one device connected.";
	echo "";
    echo "  -d [install dir name]: specify the install directory.";
    echo "	     e.g. /data/data/socwatch -- the socwatch user files will then be installed at /data/data/socwatch.";
	echo "       Defaults to /data/socwatch.";
}

check_connected_device()
{
    target_dir_test=`$ADB shell ls 2>&1`;
    if [[ $target_dir_test == *"error"* ]] ; then
        echo
        echo Please, pass connected device name with -s option.
        echo
		adb devices
        exit 255; # -1
	fi
}

check_target_dir()
{
    target_dir="$1";
    target_dir_test=`$ADB shell ls $target_dir`;
    if [[ ! $target_dir_test == *"No such file or directory"* ]] ; then
        echo
        echo   File or directory $target_dir already exists on the device.
        echo   Please specifiy different installation path.
        exit 255; # -1
	fi
}

make_dir()
{
    dir_name=$1;
    echo "Told to create dir ${dir_name}";
    ${ADB} shell mkdir -p ${dir_name};
    retVal=$?;
    if [ $retVal -ne 0 ]; then
        echo "ERROR creating dir ${dir_name}";
        usage;
        exit 255; # -1
    fi
    return $retVal;
}

install_file()
{
    file_name=$1;
    echo "Installing ${file_name}";
    ${ADB} install -r ${file_name};
    retVal=$?;
    if [ $retVal -ne 0 ]; then
        echo "ERROR installing ${file_name}";
        exit 255; #-1
    fi
    return $retVal;
}

copy_file()
{
    file_name=$1; dir_name=$2;
    echo "Copying ${file_name} to ${dir_name}";
    ${ADB} push ${file_name} ${dir_name};
    retVal=$?;
    if [ $retVal -ne 0 ]; then
        echo "ERROR copying ${file_name}";
        exit 255; #-1
    fi
    return $retVal;
}

while [ $# -gt 0 ]; do
    case $1 in
        "-s") shift; dev_name=$1;;
        "-d") shift; dir_name=$1;;
        *) usage; exit 255;;
    esac
    shift
done

if [ "Z$dev_name" != "Z" ]; then
    ADB="${ADB} -s ${dev_name} wait-for-device";
	check_connected_device
else
	ADB="${ADB} wait-for-device";
fi

if [ "Z$dir_name" != "Z" ]; then
    TARGET_DIR=${dir_name};
else
    TARGET_DIR="${BASE_DIR}/socwatch"
fi

DRIVER_DIR="${TARGET_DIR}/driver"

${ADB} root
# check target dir existence - exit if it alreday exists
check_target_dir $TARGET_DIR

echo "Using ADB_CMD = ${ADB}"
#echo "Using BASE_DIR = ${BASE_DIR}"
echo "Using TARGET_DIR = ${TARGET_DIR}"
#echo "Using DRIVER_DIR = ${DRIVER_DIR}"

# Create the various directories...
#make_dir $BASE_DIR
make_dir $TARGET_DIR
#make_dir $TARGET_DIR/libs
#make_dir $TARGET_DIR/tangier_sochap
#make_dir $TARGET_DIR/valleyview_sochap
#make_dir $DRIVER_DIR

# ...and copy over driver files...
#copy_file driver/socwatch1_0.ko ${DRIVER_DIR}
#copy_file socwatch_driver/socwatch${DRIVER_MAJOR}_${DRIVER_MINOR}.ko ${DRIVER_DIR}
#copy_file visa_driver/src/intel_visa1_1.ko ${DRIVER_DIR}
# ...and finally, the userspace files
copy_file socwatch ${TARGET_DIR}
copy_file setup_socwatch_env.sh ${TARGET_DIR}
copy_file SOCWatchConfig.txt ${TARGET_DIR}
copy_file libs ${TARGET_DIR}/libs/
copy_file valleyview_sochap ${TARGET_DIR}/valleyview_sochap/
copy_file tangier_sochap ${TARGET_DIR}/tangier_sochap/
copy_file anniedale_sochap ${TARGET_DIR}/anniedale_sochap/
copy_file cherryview_sochap ${TARGET_DIR}/cherryview_sochap/
# P.S.: exec perms don't survive the "adb push" process on Windows: force set the perms for 'socwatch' here.
echo "Changing file perms for \"socwatch\""
${ADB} shell chmod 766 ${TARGET_DIR}/socwatch
echo "All done."
exit 0
