dev:
	ENV_FILE=.env.development uv run main.py

prod:
	ENV_FILE=.env.production uv run main.py

db-upgrade:
	uv run alembic upgrade head
