# Build stage
FROM node:18-alpine as builder

WORKDIR /app

COPY package.json ./
RUN npm install

COPY public ./public
COPY src ./src

ENV REACT_APP_API_URL=http://localhost:8000

RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/build ./build

EXPOSE 3000

CMD ["serve", "-s", "build", "-l", "3000"]
