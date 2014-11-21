@echo off
rem  ***************************************************************************************
rem  Copyright 2014 Intel Corporation. All rights reserved.
rem  Other names and brands may be claimed sa the property of others.
rem  Internal use only -- Do Not Distribute
rem  ***************************************************************************************
rem
rem A rudimentary script to copy the driver
rem and support files to the Android
rem target data.

SETLOCAL

rem Set adb device number
set ADB=adb wait-for-device
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
	) else (
        set ADB=adb -s %dev_name% wait-for-device
        for /f "delims=" %%a in ('%ADB% shell ls') do @set  target_dir_test=%%a
        echo.%target_dir_test% | findstr "error" 1>nul
        if errorlevel 1 (
           echo.
           echo Please, pass connected device name with -s option.
           echo.
		   adb devices
           exit /B 1
        )
	)
) else (
    if "Z%dev_name_op%"=="ZG" (
	    echo.
        echo Please, pass device name with -s option.
	    echo.
	    call:usage
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

%ADB% root

rem Create the various directories...
rem target_dir_test=`adb shell ls %%TARGET_DIR%%`
for /f "delims=" %%a in ('%ADB% shell ls %%TARGET_DIR%%') do @set  target_dir_test=%%a
echo.%target_dir_test% | findstr "No such file or directory" 1>nul
if errorlevel 1 (
   echo.
   echo   File or directory %TARGET_DIR% already exists on the device.
   echo   Please specifiy different installation path.
   exit /B 1
)

echo Using ADB_CMD = %ADB%
echo Using TARGET_DIR = %TARGET_DIR%

tools\dos2unix.exe setup_socwatch_env.sh
tools\dos2unix.exe SOCWatchConfig.txt

call:make_dir %TARGET_DIR%
if errorlevel 1 (
   exit /B 1
   )

rem ...and copy over driver files...
rem call:copy_file socwatch_driver\socwatch%DRIVER_MAJOR%_%DRIVER_MINOR%.ko %DRIVER_DIR%
rem call:copy_file visa_driver\src\intel_visa1_1.ko %DRIVER_DIR%
rem ...and finally, the userspace files
call:copy_file socwatch %TARGET_DIR%
if errorlevel 1 (
   exit /B 1
   )
call:copy_file setup_socwatch_env.sh %TARGET_DIR%
if errorlevel 1 (
   exit /B 1
   )
call:copy_file SOCWatchConfig.txt %TARGET_DIR%
if errorlevel 1 (
   exit /B 1
   )
call:copy_file libs %TARGET_DIR%/libs/
if errorlevel 1 (
   exit /B 1
   )
call:copy_file valleyview_sochap %TARGET_DIR%/valleyview_sochap/
if errorlevel 1 (
   exit /B 1
   )
call:copy_file tangier_sochap %TARGET_DIR%/tangier_sochap/
if errorlevel 1 (
   exit /B 1
   )
call:copy_file anniedale_sochap %TARGET_DIR%/anniedale_sochap/
if errorlevel 1 (
   exit /B 1
   )
call:copy_file cherryview_sochap %TARGET_DIR%/cherryview_sochap/
if errorlevel 1 (
   exit /B 1
   )
rem P.S.: exec perms don't survive the "adb push" process on Windows: force set the perms for 'socwatch' here.
echo "Changing file permissions for socwatch"
%ADB% shell chmod 766 %TARGET_DIR%/socwatch
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

:make_dir
    set dir_name=%~1
    echo "Told to create dir %dir_name%"
    %ADB% shell mkdir -p %dir_name%
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
    %ADB% install -r %file_name%
    if errorlevel 1 (
        echo "ERROR install %file_name%"
        call:usage
        exit /B 255
    )
	exit /B
goto:eof

:copy_file
    set file_name=%~1
	set dir_name=%~2
    echo "Copying %file_name% to %dir_name%"
    %ADB% push %file_name% %dir_name%
    if errorlevel 1 (
        echo "ERROR copying %file_name%"
        call:usage
        exit /B 255
    )
	exit /B
goto:eof
