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
docker run --name app -v "$(pwd)/upload.log:/upload.log" -v "$(pwd)/configs:/app/configs" delta_sharing_upload-app
```

***Финальный тест:***
```
docker run --name app  -v "$(pwd)/upload.log:/upload.log" -v "$(pwd)/postgres.conf:/app/postgres.conf" -v "$(pwd)/mindbox.conf:/app/mindbox.conf" -v "$(pwd)/php.conf:/app/php.conf" -v "$(pwd)/yandex.conf:/app/yandex.conf" -v "$(pwd)/Profile.json:/app/Profile.json" yaroslavmd/delta_sharing_upload:latest
docker run --name app  -v "$(pwd)/upload.log:/upload.log" -v "$(pwd)/configs:/app/configs" yaroslavmd/delta_sharing_upload:latest
```


***После сборки образа:***

Тегаем: 
```
docker tag delta_sharing_upload-app:latest yaroslavmd/delta_sharing_upload:latest
```

Пушим:
```
docker push yaroslavmd/delta_sharing_upload:latest
```

if (docker ps -a --filter "name=app" --format "{{.ID}}" | Select-String .) { docker stop app 2>$null; docker rm app 2>$null }; docker images --filter=reference="yaroslavmd/delta_sharing_upload" --format "{{.ID}}" | ForEach-Object { docker rmi -f $_ } 2>$null; docker run --name app -v "$PWD\upload.log:/upload.log" -v "$PWD\configs:/app/configs" yaroslavmd/delta_sharing_upload:latest
