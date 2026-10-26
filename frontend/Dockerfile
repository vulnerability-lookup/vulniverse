FROM node:24-alpine AS dependencies
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM dependencies AS development
COPY frontend/ /app/frontend/
COPY schemas/ /app/schemas/
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM dependencies AS build
COPY frontend/ /app/frontend/
COPY schemas/ /app/schemas/
RUN npm run build

FROM nginx:stable-alpine AS production
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist/ /usr/share/nginx/html/
EXPOSE 80
