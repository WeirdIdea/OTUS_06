## Домашнее задание API скоринга

*Задание*: реализовать декларативный язык описания и систему валидации запросов к HTTP API сервиса скоринга. Шаблон уже есть в api.py, тесты в test.py, функционал подсчета скора в scoring.py. API необычно тем, что пользователи дергают методы POST запросами. Чтобы получить результат пользователь отправляет в POST запросе валидный JSON определенного формата на локейшн /method. 

*Disclaimer*: данное API ни в коей мере не являет собой best practice реализации подобных вещей и намеренно сделано "странно" в некоторых местах.

*Цель задания*: применить знания по ООП на практике, получить навык разработки нетривиальных объектно-ориентированных программ. Это даст возможность быстрее и лучше понимать сторонний код (библиотеки или сервисы часто бывают написаны с примененем ООП парадигмы или ее элементов), а также допускать меньше ошибок при проектировании сложных систем.

*Критерии успеха*: задание __обязательно__, критерием успеха является работающий согласно заданию код, для которого написаны тесты, проверено соответствие pep8, написана минимальная документация с примерами запуска (боевого и тестов), в README, например. Далее успешность определяется code review.

#### Структура запроса
```
{"account": "<имя компании партнера>", "login": "<имя пользователя>", "method": "<имя метода>", "token": "<аутентификационный токен>", "arguments": {<словарь с аргументами вызываемого метода>}}
```
* account - строка, опционально, может быть пустым
* login - строка, обязательно, может быть пустым
* method - строка, обязательно, может быть пустым
* token - строка, обязательно, может быть пустым
* arguments - словарь (объект в терминах json), обязательно, может быть пустым

#### Валидация
запрос валиден, если валидны все поля по отдельности

#### Структура ответа
OK:
```
{"code": <числовой код>, "response": {<ответ вызываемого метода>}}
```
Ошибка:
```
{"code": <числовой код>, "error": {<сообщение об ошибке>}}
```

#### Аутентификация:
смотри check_auth в шаблоне. В случае если не пройдена, нужно возвращать
```{"code": 403, "error": "Forbidden"}```

### Методы
#### online_score.
__Аргументы__
* phone - строка или число, длиной 11, начинается с 7, опционально, может быть пустым
* email - строка, в которой есть @, опционально, может быть пустым
* first_name - строка, опционально, может быть пустым
* last_name - строка, опционально, может быть пустым
* birthday - дата в формате DD.MM.YYYY, с которой прошло не больше 70 лет, опционально, может быть пустым
* gender - число 0, 1 или 2, опционально, может быть пустым

__Валидация аругементов__
аргументы валидны, если валидны все поля по отдельности и если присутсвует хоть одна пара phone-email, first name-last name, gender-birthday с непустыми значениями.
