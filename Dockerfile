FROM python:3.10.5-slim-buster AS base

RUN python -m pip install --upgrade pip
COPY requirements.txt .
RUN pip install --user -r requirements.txt

COPY ./src /app
WORKDIR    /app

ENV SHELL=/bin/bash

CMD ["python", "-u", "./main.py"]
