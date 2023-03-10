FROM node:18-buster-slim

WORKDIR /app
ADD . /app/

RUN npm ci
RUN npm run build

# start command
CMD [ "npm", "serve" ]
