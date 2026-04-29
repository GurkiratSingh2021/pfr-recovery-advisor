#!/bin/bash
gunicorn -k uvicorn.workers.UvicornWorker -b :$PORT app.main:appaz webapp up --runtime "PYTHON:3.11" --name pfr-backend-gurkirat --