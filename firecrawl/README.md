# Firecrawl Self-Hosted

Web scraping API for LLM-ready markdown. Includes:
- API server (port 3002)
- Playwright browser service
- Redis for job queue
- RabbitMQ for message queue

## Prerequisites
- Docker + Docker Compose (v2, not v1)
- 8GB+ RAM recommended (Playwright is memory-hungry)

## Deploy

```bash
cd firecrawl
docker compose --env-file .env up -d
```

API will be available at `http://your-server:3002`

## Hermes Config

In your Hermes config, set:

```yaml
web:
  search_backend: searxng  # or keep your existing
  extract_backend: firecrawl
  firecrawl:
    url: http://your-opal-server:3002
```

## Notes
- Self-hosted instances skip the Fire-engine (no IP rotation, advanced anti-bot features)
- API keys optional when using self-hosted (unlike cloud API)
- Set `BULL_AUTH_KEY` if exposing admin UI publicly