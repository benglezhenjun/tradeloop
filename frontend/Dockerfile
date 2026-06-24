FROM node:22-slim AS build
# 镜像源可配（默认国际源；国内构建可传 NPM_REGISTRY，见 README Docker 段）
ARG NPM_REGISTRY=https://registry.npmjs.org
RUN corepack enable
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm config set registry ${NPM_REGISTRY} && pnpm install --frozen-lockfile
COPY frontend ./
ENV VITE_API_URL=http://localhost:8000
RUN pnpm build

FROM nginx:alpine
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
