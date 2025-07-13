FROM python:3.10

ENV PYTHONUNBUFFERED 1

WORKDIR /Backend

COPY ./requirements.txt /requirements.txt

RUN pip install --upgrade -r /requirements.txt

RUN pip install GitPython

COPY . ./

RUN python manage.py collectstatic --noinput

RUN pip install google-generativeai
