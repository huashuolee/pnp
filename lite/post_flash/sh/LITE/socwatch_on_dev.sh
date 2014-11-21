case_name=$1
case_time=$2
bw=$3
cd /data/socwatch/
. ./setup_socwatch_env.sh
sleep 2
echo "[SETUP_SOCWATCH_ENV DONE]"
. ./init.sh
echo "[DRIVER INSMOD DONE]"
#./socwatch --max-detail -f cstate -f pstate -f wakelock -f ncstates -f scres -f intr -t $case_time -o ./results/$case_name -s 20&
#./socwatch --max-detail -f cstate -f pstate -f wakelock -f ncstates -f scres -t $case_time -o ./results/$case_name -s 20&
if [ "$bw" == "NONE" ]; then
    ./socwatch --max-detail -f cstate -f pstate -f wakelock -f ncstates -f scres -t $case_time -o ./results/$case_name &
else
    ./socwatch --max-detail -f cstate -f pstate -f wakelock -f ncstates -f scres -f $bw -t $case_time -o ./results/${case_name}_$bw &
fi

if [ "$case_name" == "usermode" ]; then
    ./usermode.sh &
fi
