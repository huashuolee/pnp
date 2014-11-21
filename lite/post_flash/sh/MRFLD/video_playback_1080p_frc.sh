cd /data/socwatch/
. ./setup_socwatch_env.sh
sleep 2
echo "[SETUP_SOCWATCH_ENV DONE]"
. ./init.sh
echo "[DRIVER INSMOD DONE]"
./socwatch --max-detail -f cstate -f pstate -f wakelock -f ncstates -f scres -f ddr-bw -t $1 -o ./results/video_playback_1080p_frc -s 20&
