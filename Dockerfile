FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir -r requirements.txt
