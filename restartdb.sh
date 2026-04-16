docker compose down
sudo rm -rf data
rm -rf /tmp/rt/*
mkdir -p data/logs/rt data/db data/sp
chmod -R 777 data
docker compose up -d
