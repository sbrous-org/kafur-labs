.PHONY: help prereq build up down clean logs bot-logs

help:
	@echo "🗺️  Assam Travel Bot — Available commands:"
	@echo ""
	@echo "  make prereq    Setup environment (copy .env, prompt for API key)"
	@echo "  make build     Build Docker images"
	@echo "  make up        Start containers in background (-d mode)"
	@echo "  make down      Stop containers"
	@echo "  make clean     Stop & remove containers, volumes, images"
	@echo "  make logs      Show all container logs"
	@echo "  make bot-logs  Show bot API logs only"
	@echo ""
	@echo "Quick start:"
	@echo "  make prereq && make build && make up"
	@echo "  Then open: http://localhost:3000"
	@echo ""

prereq:
	@echo "📋 Setting up environment..."
	@if [ -f .env ]; then \
		echo "⚠️  .env already exists. Skipping."; \
	else \
		cp .env.example .env; \
		echo "✓ Copied .env.example to .env"; \
	fi
	@echo ""
	@echo "🔑 Enter your API keys:"
	@echo ""
	@read -p "Enter ANTHROPIC_API_KEY (Claude - recommended, cheapest): " api_key; \
	if [ -n "$$api_key" ]; then \
		sed -i "s|ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$$api_key|" .env; \
		echo "✓ Anthropic API key set"; \
	fi
	@echo ""
	@read -p "Enter OPENWEATHER_API_KEY (optional, leave blank to skip): " weather_key; \
	if [ -n "$$weather_key" ]; then \
		sed -i "s|OPENWEATHER_API_KEY=.*|OPENWEATHER_API_KEY=$$weather_key|" .env; \
		echo "✓ Weather API key set"; \
	fi
	@echo ""
	@echo "✅ Environment setup complete"
	@echo ""
	@echo "Next: make build && make up"

build:
	@echo "🔨 Building Docker images..."
	docker-compose build
	@echo "✅ Build complete"

up:
	@echo "🚀 Starting containers (detach mode)..."
	docker-compose up -d
	@echo ""
	@echo "✅ Containers started!"
	@echo ""
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo ""
	@echo "🌐 Frontend: http://localhost:3000"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "View logs: make logs"
	@echo "Stop: make down"

down:
	@echo "⏹️  Stopping containers..."
	docker-compose down
	@echo "✅ Containers stopped"

clean:
	@echo "🧹 Cleaning up everything..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleanup complete"
	@echo ""
	@echo "Removed: containers, volumes, stopped images"

logs:
	@echo "📋 Showing all container logs (Ctrl+C to exit)..."
	docker-compose logs -f

bot-logs:
	@echo "📋 Showing bot API logs (Ctrl+C to exit)..."
	docker-compose logs -f bot

status:
	@echo "📊 Container status:"
	docker-compose ps

ps:
	@echo "📊 Container status:"
	docker-compose ps
