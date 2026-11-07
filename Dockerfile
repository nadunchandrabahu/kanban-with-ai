FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

RUN pip install --no-cache-dir uv

COPY backend/ /app/backend/
RUN cd /app/backend && uv pip install --system .

COPY --from=frontend-build /frontend/out /app/frontend-dist

ENV FRONTEND_DIST=/app/frontend-dist
ENV DATABASE_PATH=/app/data/pm.db
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8000"]
