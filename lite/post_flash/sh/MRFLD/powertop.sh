cd /data/powertop/
sleep 2
echo "START RUN POWERTOP IN THE BACKGROUND"
./powertop -d -t 140  > loggg  &
