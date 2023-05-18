## Управление базой данных

#### ***Программа предназначена для создания базы данных клиентов и управления ей при помощи СУБД PostgreSQL.***

### Установка:
1. Клонировать репозиторий.
```
git clone ссылка-на-репозиторий(SSH)
```
2. Установить зависимости из requrements.txt: 
```
pip install -r requirements.txt
```
3. Создать базу данных, выполнив в терминале:
```
createdb -U postgres название_БД
```
Потребуется ввести пароль для пользователя postgres.

4. Переименовать файл ".env.example" в ".env", записать в него название БД, логин и пароль для пользователя PostgreSQL, например: 
```
db_name=clients
user=postgres
password=postgres
```
5. Запустить код в IDE или выполнить в терминале:
```
python main.py
```
Следовать инструкциям.

### Формат получаемых данных:
База данных с информацией о клиентах: имя, фамилия, email, телефон (телефонов может быть несколько или не быть вообще).

### Доступные функции управления БД:
1. создать структуру БД (таблицы).
2. добавить нового клиента.
3. добавить телефон для существующего клиента.
4. изменить данные о клиенте.
5. удалить телефон для существующего клиента.
6. удалить существующего клиента.
7. найти клиента по его данным: имени, фамилии, email или телефону.
8. удалить таблицы и очистить базу данных.
