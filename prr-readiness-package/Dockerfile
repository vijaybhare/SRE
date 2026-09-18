FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY arch_compliance ./arch_compliance
COPY prr_readiness ./prr_readiness

RUN pip install --no-cache-dir -e ".[web]"

ENV PRR_WEB_HOST=0.0.0.0
ENV PRR_WEB_PORT=7860

EXPOSE 7860

CMD ["sh", "-c", "PRR_WEB_PORT=${PORT:-7860} prr-readiness-web"]
