#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

case "${1:-up}" in
  up)
    echo "Starting Kite Trader Platform..."
    docker compose up --build -d
    echo "Trader API : http://localhost:8000"
    echo "Dashboard  : http://localhost:8501"
    echo "Logs       : docker compose logs -f trader"
    ;;
  down)
    docker compose down
    ;;
  logs)
    docker compose logs -f trader
    ;;
  restart)
    docker compose restart trader
    ;;
  *)
    echo "Usage: $0 [up|down|logs|restart]"
    exit 1
    ;;
esac
