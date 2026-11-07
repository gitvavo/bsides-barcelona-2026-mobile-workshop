FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.12 uvicorn==0.34.2
COPY backend/ /app/
RUN mkdir -p /app/data
ENV MOCKAPP_DB=/app/data/mockapp.sqlite3
EXPOSE 8000 9443 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# Downloadable workshop materials: served only by the local lab-settings portal.
COPY frida/ /app/portal/downloads/frida/
COPY app/ /app/portal/downloads/app/
COPY burp/ /app/portal/downloads/burp/
COPY slides/ /app/portal/downloads/slides/
COPY setup/ /app/portal/downloads/setup/
