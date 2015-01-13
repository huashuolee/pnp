#!/bin/bash

sqlite3 ./settings.db "update system set value='44' where name='screen_brightness';"
sqlite3 ./settings.db "update system set value='0' where name='accelerometer_rotation'";
