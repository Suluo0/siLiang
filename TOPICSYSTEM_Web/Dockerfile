FROM node:22-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install

COPY . .
RUN npm run build

# ── Nginx 运行时 ──
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# SPA 路由 + API 反向代理
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
