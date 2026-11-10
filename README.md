# self-host

Sanitized example Docker Compose files for a self-hosted AI stack, from a home lab. These are the companion files for my "Self-Hosting AI" talk.

> **Snapshot, as-is.** These examples reflect my setup as of November 2026. They are shared for learning and reuse. I don't maintain them and can't provide support.  Expect to adapt these to your own hardware, network, and configuration.

## What's here

Each folder is one stack, with its own `compose.yaml` and `.env.example`.

| Folder | What it is |
|---|---|
| `nextcloud/` | Self-hosted Dropbox |
| `mealie/` | Self-hosted recipes, meal planner, and shopping lists |
| `ollama/` | Runs open models locally, serves them over an API, and has a web interface for chat |
| `vscode/` | VS Code in a container, reachable from a browser |
| `n8n/` | Low code / no code workflow automation |
| `windmill/` | Code based orchestrator for: scripts -> flows -> web UI |
| `open-notebook/` | Ask questions about your own documents |
| `openclaw/` | Agent gateway |
| `hermes/` | Agent gateway |

*Edit this table to match the folders you actually publish.*

## Before you run anything

1. Pick a stack and `cd` into its folder.
2. Copy the example environment file: `cp .env.example .env`
3. Open `.env` and replace every placeholder with your own values (passwords, tokens, domains, paths). Never commit your real `.env`; it is listed in `.gitignore`.
4. Review `compose.yaml` and adjust ports, volume paths, and the GPU settings to match your machine.
5. Start it: `docker compose up -d`

## What was changed for sharing

These files were sanitized before publishing:

- Secrets, tokens, and API keys are replaced with `${VARIABLES}` that you set in `.env`.
- Real domains, IP addresses, and hostnames are replaced with placeholders such as `example.com`, `192.0.2.x`, and `<your-host>`.
- Host paths, user IDs, and group IDs are generic.
- Network and exposure details are generalized, so these files show the pattern, not my actual setup.

## Common patterns across the stacks

- `restart: unless-stopped`, so containers come back after reboots or crashes.
- Secrets live in a `.env` file, not in `compose.yaml`.
- One named volume or bind mount per service for data that must persist.
- A shared Docker network so the stacks can reach each other.
- The NVIDIA GPU reservation (`deploy.resources.reservations.devices`) only where a container needs it, such as Ollama.

## Notes

- Pin image tags in your own copy so a future upstream change doesn't break your stack.
- The Ollama stack was written around an NVIDIA GPU and Linux with Docker Compose. Other hardware, such as AMD or CPU-only, needs different settings.
- Put a reverse proxy with TLS in front of anything you expose, and don't publish admin interfaces directly to the internet.

## License

[MIT](LICENSE). Use it however you like, with no warranty.
