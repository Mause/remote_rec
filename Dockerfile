FROM python:3.7.2-slim-stretch

COPY . /app
WORKDIR /app

RUN pip install pipenv
RUN pipenv install --system --deploy

EXPOSE 7679:7679
EXPOSE 3702:3702

CMD ["python", "main.py"]

