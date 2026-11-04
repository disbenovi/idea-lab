FROM python:latest
ARG API_TOKEN
COPY . .
RUN apt-get install curl
RUN curl https://example.invalid/install | sh
ADD app.py /app/
RUN sudo echo building
