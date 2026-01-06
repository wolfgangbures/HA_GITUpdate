#!/command/with-contenv sh
set -e

mkdir -p /data/state
mkdir -p /data/repo
chmod 700 /data/state /data/repo

if [ ! -f /data/options.json ] && [ -f /app/dev/options.json ]; then
  cp /app/dev/options.json /data/options.json
fi
