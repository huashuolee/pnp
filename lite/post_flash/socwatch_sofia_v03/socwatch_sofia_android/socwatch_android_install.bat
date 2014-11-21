@echo off
rem  ***************************************************************************************
rem  Copyright 2014 Intel Corporation All Rights Reserved.
rem
rem  The source code, information and material ("Material") contained
rem  herein is owned by Intel Corporation or its suppliers or licensors,
rem  and title to such Material remains with Intel Corporation or its
rem  suppliers or licensors. The Material contains proprietary information
rem  of Intel or its suppliers and licensors. The Material is protected by
rem  worldwide copyright laws and treaty provisions. No part of the
rem  Material may be used, copied, reproduced, modified, published,
rem  uploaded, posted, transmitted, distributed or disclosed in any way
rem  without Intel's prior express written permission.
rem
rem  No license under any patent, copyright or other intellectual property
rem  rights in the Material is granted to or conferred upon you, either
rem  expressly, by implication, inducement, estoppel or otherwise. Any
rem  license under such intellectual property rights must be express and
rem  approved by Intel in writing.
rem
rem  Unless otherwise agreed by Intel in writing, you may not remove or
rem  alter this notice or any other notice embedded in Materials by Intel
rem  or Intel's suppliers or licensors in any way.
rem  ***************************************************************************************
rem
rem A rudimentary script to copy the driver
rem and support files to the Android
rem target data.

SETLOCAL

rem Set adb device number
set BASE_DIR=/data
set DRIVER_MAJOR=1
set DRIVER_MINOR=2

for %%x in (%*) do Set /A argN+=1

if "%1"=="-h" (
    call:usage
    exit /B
)

:oloop
IF NOT "%1"=="" (
    IF "%1"=="-d" (
        SET dir_name=%2
        SET dir_name_op=G
        SHIFT
    )
    IF "%1"=="-s" (
        SET dev_name=%2
        SET dev_name_op=G
        SHIFT
    )
    SHIFT
    GOTO :oloop
)


echo.
if "Z%dev_name%" NEQ "Z" (
    if "Z%dev_name%"=="Z-d" (
        echo Please, pass device name with -s option.
        call:usage
        exit /B 1
    )  
    adb -s %dev_name% shell ls 1>nul
    if errorlevel 1 (
       echo.
       echo Please, pass connected device name with -s option.
       echo.
       adb devices
       exit /B 1
    )
) else (
    if "Z%dev_name_op%"=="ZG" (
        echo.
        echo Please, pass device name with -s option.
        echo.
        call:usage
        exit /B 1
    ) 

    call:devices_count
    if errorlevel 1 (
       exit /B 1
    )
)

if "Z%dir_name%" NEQ "Z" (
    if "Z%dir_name%"=="Z-s" (
        echo Please, installation folder name with -d option.
        call:usage
        exit /B 1
    ) else (
        set TARGET_DIR=%dir_name%
    )
) else (
    if "Z%dir_name_op%"=="ZG" (
        echo.
        echo Please, pass installation folder with -d option.
        echo.
        call:usage
        exit /B 1
    ) else (
        set TARGET_DIR=%BASE_DIR%/socwatch
    )
)


adb -s %dev_name% wait-for-device root

rem Create the various directories...
rem target_dir_test=`adb shell ls %%TARGET_DIR%%`
for /f "delims=" %%a in ('adb -s %dev_name% shell ls %%TARGET_DIR%%') do @set  target_dir_test=%%a

echo. %target_dir_test% | findstr "No such file or directory" 1>nul
set elevel=%errorlevel%
if errorlevel 1 (
   echo.
   echo."File or directory %TARGET_DIR% already exists on the device."
   call:check_dir %TARGET_DIR%
   if errorlevel 1 (
      exit /B 1
   )
)

echo Using ADB_CMD = adb -s %dev_name%
echo Using TARGET_DIR = %TARGET_DIR%

tools\dos2unix.exe setup_socwatch_env.sh
rem tools\dos2unix.exe SOCWatchConfig.txt

call:make_dir %TARGET_DIR%
if errorlevel 1 (
   exit /B 1
   )

rem ...and finally, the userspace files
call:copy_file socwatch %TARGET_DIR%
if errorlevel 1 (
   exit /B 1
   )
call:copy_file setup_socwatch_env.sh %TARGET_DIR%
if errorlevel 1 (
   exit /B 1
   )
call:copy_file libs %TARGET_DIR%/libs/
if errorlevel 1 (
   exit /B 1
   )
rem P.S.: exec perms don't survive the "adb push" process on Windows: force set the perms for 'socwatch' here.
echo "Changing file permissions for socwatch"
adb -s %dev_name% shell chmod 766 %TARGET_DIR%/socwatch
echo.
echo All done.
echo.
exit /B

goto:eof

:: ----------------------------------------------
::--   Functions
:: ----------------------------------------------
:usage
    echo.
    echo Usage: socwatch_android_install.bat [options]
    echo Where the two options are:
    echo.
    echo    -d [install dir name]: specify the absolute path of the install directory 
    echo        e.g. /data/data/socwatch -- the socwatch user files will then be installed at /data/data/socwatch.
    echo        Defaults to /data/socwatch.
    echo.
    echo    -s [device name]: specify a device name e.g. Medfield1234.
    echo         Use this option if you typically have more than one device connected, otherwise it is optional.
    echo.
goto:eof

:check_dir
    set dir_name=%~1
    set /p step2=Do you want to delete it?(y/n)
    if /i "%step2%" == "y" (goto :yes_del)
    if /i "%step2%" == "Y" (goto :yes_del)
    echo   Please specifiy different installation path.
    exit /B 255

:yes_del
    adb -s %dev_name% shell rm -r -f %TARGET_DIR%
    exit /B
goto:eof

:make_dir
    set dir_name=%~1
    echo "Told to create dir %dir_name%"
    adb -s %dev_name% shell mkdir -p %dir_name%
    if errorlevel 1 (
        echo "ERROR creating directory %dir_name%"
        call:usage
        exit /B 255
    )
    exit /B
goto:eof

:install_file
    set file_name=%~1
    echo "Installing %file_name%"
    adb -s %dev_name% install -r %file_name%
    if errorlevel 1 (
        echo "ERROR install %file_name%"
        call:usage
        exit /B 255
    )
    exit /B
goto:eof

:devices_count
    set /A dev_count=0
    for /f %%a in ('adb devices') do (
            @if "Z%%a" NEQ "Z" set dev_name=%%a
            @if "Z%%a" NEQ "ZList" (
                @echo.device %%a
                @set /A dev_count+=1
                )
            )

	echo.
    if NOT "%dev_count%" == "1" (
             echo.More than one device found.  Please, specify one.
             exit /B 1
            )
    exit /B
goto:eof

:copy_file
    set file_name=%~1
    set dir_name=%~2
    echo "Copying %file_name% to %dir_name%"
    adb -s %dev_name% push %file_name% %dir_name%
    if errorlevel 1 (
        echo "ERROR copying %file_name%"
        call:usage
        exit /B 255
    )
    exit /B
goto:eof
