# Start (first run generates ~25K cases of mock data, takes ~20s)
docker compose -f docker-compose.dev.yml up --build

# Subsequent runs (instant, data persists in volume)
docker compose -f docker-compose.dev.yml up

# Stop
docker compose -f docker-compose.dev.yml down

# Reset mock data (delete volume and regenerate)
docker compose -f docker-compose.dev.yml down -v