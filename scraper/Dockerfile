FROM python:3.11-slim-bookworm

# Install browsers to a fixed path so the non-root scraper user can find them
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN useradd -m -u 1000 scraper

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium && \
    chmod -R 755 /ms-playwright

COPY main.py .

RUN chown -R scraper:scraper /app
USER scraper

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
