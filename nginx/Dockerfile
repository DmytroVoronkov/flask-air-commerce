FROM nginx:latest

# Видаляємо стандартну конфігурацію Nginx
RUN rm /etc/nginx/conf.d/default.conf

# Копіюємо кастомну конфігурацію Nginx
COPY nginx/nginx.conf /etc/nginx/conf.d/nginx.conf

# Відкриваємо порт 80
EXPOSE 80