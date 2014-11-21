#! /bin/bash
# Initialize the device

SERIAL=`adb get-serialno`

#echo "SERIAL = $SERIAL"

if [ "$SERIAL" = "Medfield402AAC8C" ]; then
    echo "***************  Init the Merrifield VV BOARD FROM VIDEO TEAM LZY ***************"
    sh dev/Medfield402AAC8C.sh

elif [ "$SERIAL" = "Medfield69A6572C" ]; then
    echo "*****************  Init the Baytrail-tablet *****************"
    sh dev/Medfield69A6572C.sh

elif [ "$SERIAL" = "BaytrailT0219270243" ]; then
    echo "*****************  Init the Baytrail-tablet  FFRD10*****************"
    sh dev/Medfield69A6572C.sh

elif [ "$SERIAL" = "INV131700489" ]; then
    echo "*****************  Init the Merrifield SALTBAY - PR1 *****************"
    sh dev/INV131700489.sh

elif [ "$SERIAL" = "INV133600702" ]; then
    echo "the Merrifield SALTBAY - PR2 *****************"
    sh dev/INV133600702.sh

elif [ "$SERIAL" = "Medfield3C1D2C74" ]; then
    echo "*****************  Init the Merrifield SALTBAY - PR2 *****************"
    sh dev/Medfield3C1D2C74.sh

elif [ "$SERIAL" = "Medfield2B0E3BF9" ]; then
    echo "*****************  Init the Merrifield SALTBAY - PR2 *****************"
    sh dev/Medfield2B0E3BF9.sh

elif [ "$SERIAL" = "MedfieldCE80AB8C" ]; then
    echo "*****************  Init the Merrifield SALTBAY - PR2 *****************"
    sh dev/MedfieldCE80AB8C.sh

elif [ "$SERIAL" = "INV140400609" ]; then
    echo "*****************  Init the MOOREFIELD PRH *****************"
    sh dev/INV140400609.sh

elif [ "$SERIAL" = "INV141300129" ]; then
    echo "*****************  Init the MOOREFIELD PRH B0 *****************"
    sh dev/INV141300129.sh

elif [ "$SERIAL" = "INV141300219" ]; then
    echo "*****************  Init the MOOREFIELD PRH B0 *****************"
    sh dev/INV141300219.sh

elif [ "$SERIAL" = "INV141400131" ]; then
    echo "*****************  Init the MOOREFIELD PRH B0 *****************"
    sh dev/INV141400131.sh

elif [ "$SERIAL" = "004999010640000" ]; then
    echo "*****************  Init Sofia *****************"
    sh dev/Sofia0123456789ABCDEF.sh
else
    echo "!!! ATTENTION: DEVICE $SERIAL NOT REGISTERED IN dev_init.sh !!!"
    sh dev/Merrifield.sh
fi

echo "DEV_INIT.SH EXECUTION DONE"
