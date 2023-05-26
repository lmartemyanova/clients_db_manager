import os
import re
import pandas as pd
import phonenumbers
import psycopg2
from dotenv import load_dotenv, find_dotenv
from email_validator import validate_email
from psycopg2 import Error


class User:

    def __init__(self):
        load_dotenv(find_dotenv())
        self.db_name = os.getenv('db_name')
        self.user = os.getenv('user')
        self.password = os.getenv('password')


def validate_mail(email):
    try:
        email_info = validate_email(email, check_deliverability=False)
        return email_info.normalized
    except ValueError as e:
        print(str(e))
        print('Вы ввели некорректный адрес эл. почты.')
        return None


def validate_phone(phone):
    try:
        p = phonenumbers.parse(phone)
        valid_number = phonenumbers.is_valid_number(p)
        if valid_number:
            phone = phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            return phone
        else:
            print(f'Номер {phone} не валиден. ')
            return None
    except Exception:
        print(f'Номер {phone} не существует. Попытайтесь ввести номер заново с помощью команды "3".')
        return None


def validate_name(name):
    pattern = r'^[A-Za-zА-Яа-я]+$'  # Name can contain Latin and Cyrillic letters
    return bool(re.match(pattern, name))


def create_tables(cur):
    cur.execute("""
                    CREATE TABLE IF NOT EXISTS clients(
                    client_id SERIAL PRIMARY KEY,
                         name VARCHAR(200) NOT NULL,
                      surname VARCHAR(200) NOT NULL,
                        email VARCHAR(200) NOT NULL
                    ); 
    """)
    cur.execute("""
                    CREATE TABLE IF NOT EXISTS phones(
                     phone_id SERIAL PRIMARY KEY,
                    client_id INTEGER REFERENCES clients(client_id),
                        phone TEXT UNIQUE
                    );
    """)
    try:
        conn.commit()
        print('Таблицы успешно созданы.')
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        print('Таблицы не созданы!')
    return


def add_client(cur, name, surname, email, phones=None):
    try:
        cur.execute("""
                            SELECT client_id
                            FROM clients
                            WHERE email = %s;
                            """, (email,))
        if (existing_mail := cur.fetchone()) is not None:
            print(f"Клиент с email {email} уже есть в базе данных. Id клиента: {existing_mail[0]}. ")
            return
        cur.execute("""
                    INSERT INTO clients(name, surname, email) 
                         VALUES (%s, %s, %s) 
                      RETURNING client_id;
        """, (name.capitalize(), surname.capitalize(), email))
        print("Готово! Id клиента: ", (client_id := cur.fetchone())[0])
        conn.commit()
    except (Exception, Error) as error:
        print("Ошибка добавления клиента в Базу данных: ошибка при работе с PostgreSQL", error)
        return
    if phones is not None:
        for phone in phones:
            if phone is not None:
                try:
                    cur.execute("""
                    INSERT INTO phones(client_id, phone)
                         VALUES (%s, %s)
                      RETURNING phone_id;
                    """, (client_id, phone))
                    print(f"Телефон {phone} добавлен для клиента {client_id[0]}, id: {cur.fetchone()[0]}")
                    conn.commit()
                except psycopg2.errors.ForeignKeyViolation:
                    print(f"Ошибка добавления телефона {phone} в Базу данных: нет пользователя с id {client_id}.")
                    return
                except (Exception, Error) as error:
                    print("Ошибка добавления телефона: ошибка при работе с PostgreSQL", error)
                    return
    return


def add_phone(cur, client_id, phone):
    cur.execute("""
                SAVEPOINT before_add_phone;
    """)
    try:
        cur.execute("""
                    INSERT INTO phones(client_id, phone)
                         VALUES (%s, %s)
                      RETURNING phone_id;
                    """, (client_id, phone))
        print(f"Номер {phone} c id {cur.fetchone()[0]} успешно добавлен для клиента {client_id}")
        conn.commit()
    except psycopg2.errors.ForeignKeyViolation:
        print("Клиента с таким id нет в базе данных. ")
        return
    except psycopg2.errors.UniqueViolation:
        cur.execute("""
                    ROLLBACK TO SAVEPOINT before_add_phone;
        """)
        conn.commit()
        cur.execute("""
                    SELECT phone_id, 
                           client_id 
                      FROM phones
                     WHERE phone = %s;
                    """, (phone,))
        print(f"Номер {phone} уже зарегистрирован для клиента id {cur.fetchall()[0][1]}.")
        return
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        return
    return


def delete_phone(cur, client_id, phone):
    try:
        cur.execute("""
                    SELECT phone_id 
                      FROM phones
                     WHERE client_id = %s AND
                           phone = %s;
                    """, (client_id, phone))
        phone_id = cur.fetchone()
        if phone_id is None:
            print(f"Не зарегистрирован номер {phone} для клиента {client_id}. Проверьте корректность ввода. ")
            return
        phone_id = phone_id[0]
        print(f"Вы хотите удалить телефон c id {phone_id}.")
        cur.execute("""
                    SAVEPOINT delete_phone_savepoint;
                    """)
        cur.execute("""
                    DELETE FROM phones
                     WHERE client_id = %s AND
                           phone = %s;
                    """, (client_id, phone))
        try:
            conn.commit()
            print("Номер успешно удален.")
        except psycopg2.errors.TransactionRollbackError:
            cur.execute("""
                        ROLLBACK TO SAVEPOINT delete_phone_savepoint;
                        """)
            print("Ошибка транзакции. Номер не удален. ")
        except (Exception, Error) as error:
            cur.execute("""
                        ROLLBACK TO SAVEPOINT delete_phone_savepoint;
                        """)
            print("Номер не удален. Ошибка при работе с PostgreSQL", error)
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
    return


def update_data(cur, client_id, name=None, surname=None, email=None, phones=None):
    try:
        if name is not None:
            cur.execute("""
            UPDATE clients SET name=%s
            WHERE client_id=%s;
            """, (name, client_id))
        else:
            pass
        if surname is not None:
            cur.execute("""
            UPDATE clients SET surname=%s
            WHERE client_id=%s;
            """, (surname, client_id))
        else:
            pass
        if email is not None:
            cur.execute("""
            UPDATE clients SET email=%s
            WHERE client_id=%s;
            """, (email, client_id))
        else:
            pass
        if phones is not None:
            cur.execute("""
            DELETE FROM phones 
            WHERE client_id=%s;
            """, (client_id,))
            phones_values = [(client_id, phone) for phone in phones]
            cur.executemany("""
            INSERT INTO phones (client_id, phone) 
            VALUES (%s, %s);
            """, phones_values)
        print(f"Данные пользователя {client_id} заменены. ")
        conn.commit()
        return
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        return


def delete_client(cur, client_id):
    cur.execute("""
    DELETE FROM phones 
     WHERE client_id=%s;
    """, (client_id,))
    cur.execute("""
    DELETE FROM clients 
     WHERE client_id=%s;
    """, (client_id,))
    try:
        conn.commit()
        print(f"Клиент с id {client_id} удален.")
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        print(f"Клиент не удален.")
        return
    return


def find_client(cur, data):
    cur.execute("""
    SELECT c.client_id, name, surname, email, string_agg(phone, ', ') AS phones 
    FROM clients c
    LEFT JOIN phones p ON c.client_id = p.client_id
    WHERE name = %s OR surname = %s OR email = %s OR phone = %s
    GROUP BY c.client_id;
    """, (data.capitalize(), data.capitalize(), data, data))
    try:
        result = []
        for client in cur.fetchall():
            client = [client[0], client[1], client[2], client[3], client[4]]
            result.append(client)
        df = pd.DataFrame(result, columns=['id', 'name', 'surname', 'email', 'phones'])
        df = df.sort_values(by=['id'])
        print(df.to_string(index=False))
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        return
    return


def find_client_by_id(cur, client_id):
    cur.execute("""
        SELECT c.client_id, name, surname, email, phone 
        FROM clients c
        LEFT JOIN phones p ON c.client_id = p.client_id
        WHERE c.client_id = %s;
        """, (client_id,))
    try:
        client = cur.fetchone()
        if client is None:
            print("Клиент с таким id не найден. ")
            return
        else:
            info = [(id := client[0]),
                    client[1],
                    client[2],
                    client[3],
                    [client[4] for client in clients if client[0] == id and client[4] is not None]]
            df = pd.DataFrame.from_dict({'id': [info[0]],
                                         'name': [info[1]],
                                         'surname': [info[2]],
                                         'email': [info[3]],
                                         'phones': [', '.join(info[4])]}, )
            df = df[['id', 'name', 'surname', 'email', 'phones']]
            df = df.sort_values(by=['id'])
            print(df.to_string(index=False))
            return info
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        return


def delete_tables(cur):
    try:
        cur.execute("""
        DROP TABLE phones;
        DROP TABLE clients;
        """)
        conn.commit()
        print('Таблицы удалены.')
    except psycopg2.errors.UndefinedTable:
        print("Таблицы не были созданы или уже удалены.")
        return
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        return
    return


def exit_db(conn):
    try:
        conn.close()
        print('Вы вышли из базы данных. Для работы перезапустите программу. ')
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        return


def test_functions(cur):
    create_tables(cur)
    add_client(cur,
               name="Alina",
               surname="Petrova",
               email="alinaaaa@mail.ru",
               phones=[validate_phone(phone) for phone in ["+79562948573", "+79485736", "+7-926-485-93-04"]
                       if phone is not None])
    add_client(cur,
               name="Anna",
               surname="Mass",
               email="lotus4@gmail.com",
               phones=[validate_phone(phone) for phone in ["+79840293847", "94857392"]
                       if phone is not None])
    add_phone(cur,
              client_id=2,
              phone=validate_phone("+7(948)273-64-82"))
    delete_phone(cur,
                 client_id=1,
                 phone=validate_phone("+79562948573"))
    update_data(cur,
                client_id=1,
                surname="Ivanova",
                phones=[validate_phone(phone) for phone in ["+7-958-394-85-72", "+79872049384"]])
    find_client(cur, data="Anna")
    find_client_by_id(cur, client_id=1)
    delete_client(cur, client_id=1)
    delete_tables(cur)
    return


if __name__ == '__main__':
    user = User()

    with psycopg2.connect(database=user.db_name, user=user.user, password=user.password) as conn:
        with conn.cursor() as cur:
            test_functions(cur)

    with psycopg2.connect(database=user.db_name, user=user.user, password=user.password) as conn:
        with conn.cursor() as cur:
            print("""
                    Доступные команды:
                    1. создать структуру БД (таблицы).
                    2. добавить нового клиента.
                    3. добавить телефон для существующего клиента.
                    4. изменить данные о клиенте.
                    5. удалить телефон для существующего клиента.
                    6. удалить существующего клиента.
                    7. найти клиента по его данным: имени, фамилии, email или телефону.
                    8. найти клиента по его id.
                    9. завершить работу с базой данных.
                    10. удалить таблицы и очистить базу данных.
                    """)
            while True:
                command = input("Введите номер команды: ")
                if command == '1':
                    create_tables(cur)
                elif command == '2':
                    name = input("Введите имя: ")
                    while not validate_name(name):
                        print("Некорректное имя. Попробуйте еще раз.")
                        name = input("Введите имя: ")
                    surname = input("Введите фамилию: ")
                    while not validate_name(surname):
                        print("Некорректная фамилия. Попробуйте еще раз.")
                        surname = input("Введите фамилию: ")
                    email = validate_mail(input("Введите email: "))
                    while email is None:
                        email = validate_mail(input("Введите email: "))
                    print("Введите ниже через запятую номера телефонов клиента")
                    numbers = input("Введите номер(-а) телефона c +7...: ").replace(' ', '').split(',')
                    phones = [phone for number in numbers if (phone := validate_phone(number)) is not None]
                    add_client(cur, name, surname, email, phones)
                elif command == '3':
                    client_id = int(input('Введите id клиента: '))
                    new_phone = validate_phone(input('Введите номер телефона: '))
                    if new_phone is not None:
                        add_phone(cur, client_id, new_phone)
                    else:
                        print("Номер не валиден и не будет добавлен в базу данных.")
                elif command == '4':
                    client_id = int(input('Введите id клиента: '))
                    print("Текущие данные клиента: ")
                    old_data = find_client_by_id(cur, client_id)
                    print("Поочередно введите данные, которые хотите изменить. Если данные менять не нужно, "
                          "нажмите Enter.")
                    name = input("Введите новое имя: ")
                    surname = input("Введите новую фамилию: ")
                    email = validate_mail(input("Введите новый email: "))
                    numbers = input("Введите номер(-а) телефона c +7...: ").replace(' ', '').split(',')
                    phones = [phone for number in numbers if (phone := validate_phone(number)) is not None]
                    name = name if name else None
                    surname = surname if surname else None
                    email = email if email else None
                    phones = phones if phones else None
                    update_data(cur, client_id, name, surname, email, phones)
                elif command == '5':
                    client_id = int(input('Введите id клиента: '))
                    phone = validate_phone(input('Введите номер телефона для удаления: '))
                    delete_phone(cur, client_id, phone)
                elif command == '6':
                    client_id = int(input('Введите id клиента для удалениия: '))
                    delete_client(cur, client_id)
                elif command == '7':
                    data = input("Введите данные для поиска: ")
                    if not data.isalpha():
                        try:
                            data = validate_phone(data)
                        except Exception:
                            pass
                    if "@" in data:
                        try:
                            data = validate_mail(data)
                        except Exception:
                            pass
                    find_client(cur, data)
                elif command == '8':
                    client_id = int(input('Введите id клиента: '))
                    data = find_client_by_id(cur, client_id)
                elif command == '9':
                    exit_db(conn)
                elif command == '10':
                    delete_tables(cur)
                else:
                    print('Ошибочная команда, введите команду снова.')
