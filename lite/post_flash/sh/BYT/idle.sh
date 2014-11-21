cd /data/socwatch/
. ./setup_socwatch_env.sh
sleep 2
echo "[SETUP_SOCWATCH_ENV DONE]"
. ./init.sh
echo "[DRIVER INSMOD DONE]"
./socwatch --max-detail -f cpu-cstate -f cpu-pstate  -f nc-dstate -f gfx-pstate -f gfx-cstate -t 120 -o ./results/idle -s 20&
