FROM python:3.10.0

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt

COPY . /app

ENV FLASK_APP=app.py

CMD ["flask", "run", "--host=0.0.0.0", "-p", "5000"]