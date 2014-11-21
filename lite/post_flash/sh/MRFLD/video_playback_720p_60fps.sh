cd /data/socwatch/
. ./setup_socwatch_env.sh
sleep 2
echo "[SETUP_SOCWATCH_ENV DONE]"
. ./init.sh
echo "[DRIVER INSMOD DONE]"
./socwatch --max-detail -f cstate -f pstate -f wakelock -f ncstates -f scres -t $1 -o ./results/video_playback_720p_60fps -s 20&
