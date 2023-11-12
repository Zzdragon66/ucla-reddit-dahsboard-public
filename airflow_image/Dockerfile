FROM apache/airflow:2.7.2-python3.11

ENV DEBIAN_FRONTEND=noninteractive 

USER root
RUN apt-get update -y && \
    apt-get install -y openjdk-11-jdk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN apt update && apt install -y procps
# Make sure the JAVA_HOME is set to correct path with correct architecture
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-arm64 

USER airflow
COPY .env .env
COPY python_requirements.txt python_requirements.txt

RUN pip3 install --no-cache-dir 'apache-airflow-providers-apache-spark'
RUN pip3 install -r ./python_requirements.txt

USER root
RUN chmod 644 /opt/airflow/.env

USER airflow