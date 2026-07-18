#!/bin/bash
# Docker deployment script for Video Generator

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Video Generator Docker Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo -e "Creating .env from .env.docker template..."
    cp .env.docker .env
    echo -e "${RED}Please edit .env file with your API keys before continuing${NC}"
    exit 1
fi

# Parse command line arguments
ACTION=${1:-up}

case $ACTION in
    up)
        echo -e "${GREEN}Starting all services...${NC}"
        docker compose up -d
        
        echo -e "${YELLOW}Waiting for MySQL to be ready...${NC}"
        sleep 10
        
        echo -e "${GREEN}Initializing database...${NC}"
        docker compose run --rm db-init
        
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  Deployment Complete!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo -e "Frontend: http://localhost:80"
        echo -e "Backend API: http://localhost:8000"
        echo -e "API Docs: http://localhost:8000/docs"
        ;;
    
    down)
        echo -e "${YELLOW}Stopping all services...${NC}"
        docker compose down
        echo -e "${GREEN}Services stopped${NC}"
        ;;
    
    restart)
        echo -e "${YELLOW}Restarting all services...${NC}"
        docker compose restart
        echo -e "${GREEN}Services restarted${NC}"
        ;;
    
    logs)
        docker compose logs -f ${2:-}
        ;;
    
    build)
        echo -e "${GREEN}Building images...${NC}"
        docker compose build --no-cache
        echo -e "${GREEN}Build complete${NC}"
        ;;
    
    clean)
        echo -e "${RED}Warning: This will remove all containers, volumes, and images${NC}"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose down -v --rmi all
            echo -e "${GREEN}Cleanup complete${NC}"
        fi
        ;;
    
    status)
        docker compose ps
        ;;
    
    init-db)
        echo -e "${GREEN}Initializing database...${NC}"
        docker compose run --rm db-init
        echo -e "${GREEN}Database initialized${NC}"
        ;;
    
    *)
        echo "Usage: $0 {up|down|restart|logs|build|clean|status|init-db}"
        echo ""
        echo "Commands:"
        echo "  up       - Start all services"
        echo "  down     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - View logs (optionally specify service name)"
        echo "  build    - Rebuild all images"
        echo "  clean    - Remove all containers, volumes, and images"
        echo "  status   - Show service status"
        echo "  init-db  - Initialize/reset database"
        exit 1
        ;;
esac
