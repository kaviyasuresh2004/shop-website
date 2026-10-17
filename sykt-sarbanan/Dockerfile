FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production DATA_DIR=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 1000 --create-home shop && mkdir /data && chown shop:shop /data
COPY --chown=shop:shop app.py server.py accounts.py commerce.py inventory.py shopping.py phone_verification.py photos.py branding.py delivery.py categorisation.py shop.json index.html staff.html ./
COPY --chown=shop:shop assets ./assets
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh
CMD ["/bin/sh", "/entrypoint.sh"]
