#!/bin/sh
#  ***************************************************************************************
#  Copyright 2014 Intel Corporation All Rights Reserved.
#
#  The source code, information and material ("Material") contained
#  herein is owned by Intel Corporation or its suppliers or licensors,
#  and title to such Material remains with Intel Corporation or its
#  suppliers or licensors. The Material contains proprietary information
#  of Intel or its suppliers and licensors. The Material is protected by
#  worldwide copyright laws and treaty provisions. No part of the
#  Material may be used, copied, reproduced, modified, published,
#  uploaded, posted, transmitted, distributed or disclosed in any way
#  without Intel's prior express written permission.
#
#  No license under any patent, copyright or other intellectual property
#  rights in the Material is granted to or conferred upon you, either
#  expressly, by implication, inducement, estoppel or otherwise. Any
#  license under such intellectual property rights must be express and
#  approved by Intel in writing.
#
#  Unless otherwise agreed by Intel in writing, you may not remove or
#  alter this notice or any other notice embedded in Materials by Intel
#  or Intel's suppliers or licensors in any way.
#  ***************************************************************************************
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
# =============================================================================

export SOCWATCH_INSTALL_PATH=`pwd`
echo SOCWATCH is currently installed under $SOCWATCH_INSTALL_PATH
# export SOCWATCH_CONFIG_DIR="${SOCWATCH_INSTALL_PATH}"
# echo "SOCWATCH_CONFIG_DIR=${SOCWATCH_CONFIG_DIR}" 

export PATH="${SOCWATCH_INSTALL_PATH}:${PATH}"
export LD_LIBRARY_PATH="${SOCWATCH_INSTALL_PATH}/libs:${LD_LIBRARY_PATH}"

# show settings of various environment variables
echo "PATH=${PATH}"
echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"
echo ""
echo "If you haven't installed the driver yet, do the following steps:"
echo "\> insmod /system/lib/modules/socwatch0_3.ko"
