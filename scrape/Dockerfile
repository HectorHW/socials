FROM python:3.10
COPY . .

RUN --mount=type=cache,target=/root/.cache pip3 install -r requirements.txt

COPY src/ src

CMD [ "python", "src/app.py" ]