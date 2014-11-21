#!/bin/bash

case_name=$1
case_time=$2
bw=$3

function run_socwatch() {
case_name=$1
case_time=$2
bw=$3
echo "[##### SOCWATCH $case_name CASE START #####]"
adb root
sleep 2
adb shell << EOF
cd /data/socwatch/
./socwatch_on_dev.sh $case_name $case_time $bw
cd ..
exit
EOF
echo "[##### SOCWATCH $case_name CASE END #####]"

}

run_socwatch $case_name $case_time $bw &

#./socwatch_on_dev.sh $case_name $case_time $bw
#cd powertop
#./powertop.sh
