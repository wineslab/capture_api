
# Production stage
FROM nginx:alpine

WORKDIR /app

COPY . .

# Copy built React app to Nginx static directory
COPY /app/public /usr/share/nginx/html/frontend

COPY nginx.conf /etc/nginx/nginx.conf


# Expose the port for serving the app
EXPOSE 80

# Command to start Nginx
CMD ["nginx", "-g", "daemon off;"]
