FROM python:3.12
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1

ADD . /app
WORKDIR /app
RUN uv sync --frozen

ENTRYPOINT [ "uv", "run", "main.py", "--client=slack" ]