#!/bin/bash

function set_cpu_freq() {
cpuid=$1
cpufreq=$2

adb wait-for-device
adb shell "echo $cpufreq > /sys/devices/system/cpu/$cpuid/cpufreq/scaling_min_freq"
adb wait-for-device
adb shell "echo $cpufreq > /sys/devices/system/cpu/$cpuid/cpufreq/scaling_max_freq"
echo "**************************"
echo "$cpuid "
echo "scaling_min_freq "
adb shell "cat /sys/devices/system/cpu/$cpuid/cpufreq/scaling_min_freq"
echo "scaling_max_freq "
adb shell "cat /sys/devices/system/cpu/$cpuid/cpufreq/scaling_max_freq"
}

echo " ****************************** "
echo " SET CPU FREQUENCE 1333Mhz      "
echo " ****************************** "
adb wait-for-device
adb root


set_cpu_freq cpu0 1333000
set_cpu_freq cpu1 1333000
set_cpu_freq cpu2 1333000
set_cpu_freq cpu3 1333000
