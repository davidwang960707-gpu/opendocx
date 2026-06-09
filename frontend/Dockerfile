# OpenDocX Frontend Dockerfile
# Multi-stage: build (Vite) → serve (nginx)

FROM node:18-alpine AS builder

WORKDIR /build

# Cache deps
COPY package*.json ./
RUN npm ci || npm install

# Build
COPY . .
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

# Runtime: nginx
FROM nginx:1.27-alpine

# Custom nginx config (proxy /api → backend)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static built assets
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1
