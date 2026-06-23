FROM node:20-alpine AS build
WORKDIR /app

ARG VITE_API_BASE=/api
ARG VITE_APP_ENV=
ENV VITE_API_BASE=$VITE_API_BASE
ENV VITE_APP_ENV=$VITE_APP_ENV

COPY package.json package-lock.json ./
RUN npm ci --include=optional

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
