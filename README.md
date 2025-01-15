**Развернуть контейнер:**
```
docker run --name app 
-v "$(pwd)/upload.log:/upload.log" 
-v "$(pwd)/postgres.conf:/app/postgres.conf" 
-v "$(pwd)/mindbox.conf:/app/mindbox.conf" 
-v "$(pwd)/php.conf:/app/php.conf" 
-v "$(pwd)/yandex.conf:/app/yandex.conf" 
-v "$(pwd)/Profile.json:/app/Profile.json" 
yaroslavmd/delta_sharing_upload:latest
```

**Запуск скрипта:**
```
docker exec -it app python script.py
```

***Локальный тест:***
```
docker run --name app -v "$(pwd)/upload.log:/upload.log" -v "$(pwd)/postgres.conf:/app/postgres.conf" -v "$(pwd)/mindbox.conf:/app/mindbox.conf" -v "$(pwd)/php.conf:/app/php.conf" -v "$(pwd)/yandex.conf:/app/yandex.conf" -v "$(pwd)/Profile.json:/app/Profile.json" upload-app
```
