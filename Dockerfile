FROM python:3

WORKDIR /app

ADD src/requirements.txt requirements.txt

RUN pip install -r requirements.txt

ADD src

CMD ["python", "src/run.py"]
