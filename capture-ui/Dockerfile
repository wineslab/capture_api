# Build stage
FROM node:16-alpine as build

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package.json ./
RUN npm install

# Copy the rest of the app's source code
COPY . .

# Build the app for production
RUN npm run build

# Production stage
FROM nginx:alpine


# Copy built React app to Nginx static directory
COPY --from=build /app/build /usr/share/nginx/html/frontend

COPY nginx.conf /etc/nginx/nginx.conf


# Expose the port for serving the app
EXPOSE 80

# Command to start Nginx
CMD ["nginx", "-g", "daemon off;"]
