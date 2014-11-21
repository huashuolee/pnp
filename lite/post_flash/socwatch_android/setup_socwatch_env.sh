#!/bin/sh
#
# =============================================================================
# Filename: setup_socwatch_env.sh
# Version: 1.00
# Purpose: SOCWatch Android Runtime environment setup script
# Description: This script should be used to set up the Android OS run-time environment
#              for SOCWatch.  It requires sh.  Run this script before running any
#              SOCWatch executable, e.g., socwatch 
#
# Usage: source setup_socwatch_env.sh
#
# Copyright(C) 2004-2014 Intel Corporation.  All Rights Reserved.
# =============================================================================

export SOCWATCH_INSTALL_PATH=`pwd`
echo SOCWATCH is currently installed under $SOCWATCH_INSTALL_PATH
export VISA_BASE_DIR="${SOCWATCH_INSTALL_PATH}"
echo "VISA_BASE_DIR=${VISA_BASE_DIR}" 
export SOCWATCH_CONFIG_DIR="${SOCWATCH_INSTALL_PATH}"
echo "SOCWATCH_CONFIG_DIR=${SOCWATCH_CONFIG_DIR}" 

export PATH="${SOCWATCH_INSTALL_PATH}:${PATH}"
export LD_LIBRARY_PATH="${SOCWATCH_INSTALL_PATH}/libs:${LD_LIBRARY_PATH}"

# these steps are needed to enable visa-metrics on Anniedale, i.e. Moorefield platform

which getprop 2>&1 > /dev/null
if [ "$?" -eq "0" ] ; then
    platform=`getprop ro.board.platform`
    if [ "$platform" = "moorefield" ] ; then
        echo 15 > /d/pmu_force_d0i0
        echo 15 > /d/pmu_sync_d0ix
    fi
fi


# show settings of various environment variables
echo "PATH=${PATH}"
echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"
echo ""
echo "If you haven't installed the driver yet, do the following steps:"
echo "\> insmod /lib/modules/intel_visa1_x.ko"
echo "\> insmod /lib/modules/socwatch1_4.ko"
