FROM rabbitmq:3.13-management-alpine


# Copy config + script
COPY src/rabbitmq/ /etc/rabbitmq/


# Use bash for envsubst
RUN apk add --no-cache bash gettext


# Entrypoint to generate definitions and run RabbitMQ
ENTRYPOINT ["sh", "-c", "envsubst < /etc/rabbitmq/definitions.template.json > /etc/rabbitmq/definitions.json && rabbitmq-server"]
