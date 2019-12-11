FROM python:3.7

LABEL maintainer "Alexander Pashuk"
LABEL description "Time Synchronizer"

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y apt-utils

RUN apt-get update && apt-get install -y \
     python3-dev

# RUN apt-get install -y \
#      python3-pip

RUN apt-get update && apt-get install -y --no-install-recommends \
    uwsgi \
    uwsgi-plugin-python \
    uwsgi-plugin-python3


RUN apt-get clean \
 && apt-get autoremove \
 && rm -rf /var/lib/apt/lists/*

# Copy app
COPY ./ /opt/app/

WORKDIR /opt/app

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir uwsgi

EXPOSE 8000

CMD ["./wait-for-it.sh", "db:5432", "--", "uwsgi", "--ini", "uwsgi.ini"]
