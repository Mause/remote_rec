FROM python:3.7.2-slim-stretch

COPY . /app
WORKDIR /app

RUN pip install pipenv
RUN pipenv install --system --deploy

EXPOSE 5000:80

CMD ["python", "main.py"]

