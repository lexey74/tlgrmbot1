
создаем окружение
```bash
python -m venv .venv
```

активируем
```bash
source .venv/bin/activate  # unix
.\myenv\Scripts\Activate  # Windows
```

устанавливаем зависимости
```bash
pip install -r requirements.txt
```

Создаем необходимые каталоги
```bash
mkdir logs
mkdir chats
```

Копируем в каталог файл для работы с Google Console

Настраиваем (или копируем) файл среды 
```bash
nano .env
```

запуск (путь должен указывать на эту машину, порт 8443)
```bash
uvicorn app:app --workers 1 --host 0.0.0.0 --port 8443  # make run
```

>>>>>>> b298894 (Initial commit with local files)
