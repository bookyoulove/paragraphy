# 1. Base stage with Node.js
FROM node:20-alpine AS base
WORKDIR /app

# Install dependencies (cached)
COPY package.json package-lock.json* ./
RUN npm install

# 2. Development stage (Vite dev server with HMR)
FROM base AS development
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# 3. Builder stage for production
FROM base AS builder
COPY . .
RUN npm run build

# 4. Production stage (Nginx static serving)
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
