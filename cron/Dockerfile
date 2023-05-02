FROM ubuntu:latest

ADD crontab /etc/cron.d/python-cron

RUN chmod +x /etc/cron.d/python-cron

RUN touch /var/log/cron.log

RUN apt update -y
RUN apt install cron -y

CMD cron
