FROM python:3.12-slim AS build

WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
# No .git in the build context: hatch-vcs falls back to the configured version.
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

COPY --from=build /install /usr/local
RUN useradd --create-home --uid 10001 appuser
USER appuser

ENTRYPOINT ["scientific-data-mcp"]
CMD ["--http", "--host", "0.0.0.0", "--port", "8000"]
