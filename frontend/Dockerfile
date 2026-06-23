FROM node:22-slim AS build
RUN corepack enable
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend ./
ENV VITE_API_URL=http://localhost:8000
RUN pnpm build

FROM nginx:alpine
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
