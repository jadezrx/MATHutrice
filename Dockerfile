# The image the pipeline builds, once per commit, and deploys to Fork staging,
# then to Fork production by promotion.
#
# The Python version is the one in .python-version, so that uv uses the image's
# interpreter and never downloads another.
FROM python:3.14.7-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /bin/uv

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

# The dependencies first, without the project: this layer stays cached until
# uv.lock changes. --locked installs exactly what uv.lock pins, and fails if it
# no longer matches pyproject.toml. --no-dev leaves pytest and tach out.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY mathutrice ./mathutrice
RUN uv sync --locked --no-dev

# The commit the image is built from (`--build-arg REVISION=...`). The app sends
# it back in the X-Revision header of every response, so a deploy can tell which
# image answers, not only that one does. Last, so it keeps the layers above cached.
ARG REVISION=unknown
ENV REVISION=$REVISION

# The one process the service runs, as README.md starts it: uvicorn, whose
# lifespan creates and seeds the database and starts the hourly cleanup
# scheduler. One worker only: a second would run a second scheduler.
EXPOSE 8000
CMD ["uvicorn", "mathutrice.app:app", "--host", "0.0.0.0", "--port", "8000"]
