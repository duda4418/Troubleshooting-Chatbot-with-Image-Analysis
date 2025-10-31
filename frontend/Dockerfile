# syntax=docker/dockerfile:1.7

# ---- Build stage ----
FROM node:20-alpine AS build

WORKDIR /frontend

# Install dependencies separately to leverage Docker layer caching.
COPY package*.json ./
RUN npm install

# Copy the rest of the source and build the production bundle.
COPY . .

ARG VITE_API_BASE_URL="http://backend:8000"
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# ---- Runtime stage ----
FROM nginx:1.27-alpine AS runtime

COPY --from=build /frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
