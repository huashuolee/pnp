case_name=$1
case_time=$2
cd /data/socwatch/
. ./setup_socwatch_env.sh
sleep 2
echo "[SETUP_SOCWATCH_ENV DONE]"
. ./init.sh
echo "[DRIVER INSMOD DONE]"
#./socwatch --max-detail -f cstate -f pstate -f wakelock -f ncstates -f scres -t $case_time -o ./results/$case_name -s 20&
./socwatch --max-detail -f cpu-cstate -f cpu-pstate  -f nc-dstate -f gfx-pstate -f gfx-cstate -t $case_time -o ./results/$case_name -s 20&
