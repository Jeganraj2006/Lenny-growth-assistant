FROM node:22-bookworm-slim

WORKDIR /app
ENV HOME=/app
COPY package.json ./
RUN npm install --ignore-scripts
COPY tsconfig.json ./
COPY .pi ./.pi
COPY src ./src
RUN npm run build

EXPOSE 3001
CMD ["npm", "run", "start"]

