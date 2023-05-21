import psycopg2
from email_validator import validate_email
import phonenumbers
import os
from dotenv import load_dotenv, find_dotenv
from psycopg2 import Error


class User:

    def __init__(self):
        load_dotenv(find_dotenv())
        self.db_name = os.getenv('db_name')
        self.user = os.getenv('user')
        self.password = os.getenv('password')


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


def validate_mail(email):
    try:
        email_info = validate_email(email, check_deliverability=False)
        return email_info.normalized
    except ValueError as e:
        print(str(e))
        print('Вы ввели некорректный адрес эл. почты, попытайтесь снова.')
        email = None
        return email


def validate_phone(phone):
    try:
        p = phonenumbers.parse(phone)
        valid_number = phonenumbers.is_valid_number(p)
        if valid_number:
            phone = phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            return phone
        else:
            print(f'Номер {phone} не валиден. Попытайтесь ввести номер заново с помощью команды "3".')
    except Exception:
        print(f'Номер {phone} не существует. Попытайтесь ввести номер заново с помощью команды "3".')
        phone = None
        return phone


def add_client(cur, name, surname, email, phones=None):
    cur.execute("""
                INSERT INTO clients(name, surname, email) 
                     VALUES (%s, %s, %s) 
                  RETURNING client_id;
    """, (name.capitalize(), surname.capitalize(), email))
    try:
        print("Готово! Id клиента: ", client_id := cur.fetchone()[0])
        conn.commit()
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        print("Ошибка добавления клиента в Базу данных.")
    if phones is not None:
        for phone in phones:
            cur.execute("""
            INSERT INTO phones(client_id, phone)
                 VALUES (%s, %s)
              RETURNING phone_id;
            """, (client_id, phone))
            try:
                print(f"Телефон {phone} добавлен для клиента {client_id}, id: {cur.fetchone()[0]}")
                conn.commit()
            except (Exception, Error) as error:
                print("Ошибка при работе с PostgreSQL", error)
                print(f"Ошибка добавления телефона {phone} в Базу данных: нет пользователя с id {client_id}.")
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
    except Exception:
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
        print(f"Номер с id {(id := (cur.fetchall())[0])[0]} уже зарегистрирован для клиента id {id[1]}.")
    return


def delete_phone(cur, client_id, phone):
    cur.execute("""
                SELECT phone_id 
                  FROM phones
                 WHERE client_id = %s AND
                       phone = %s;
                """, (client_id, phone))
    try:
        print(f"Вы хотите удалить телефон c id {(phone_id := cur.fetchone()[0])}.")
        cur.execute("""
                    DELETE FROM phones
                     WHERE client_id = %s AND
                           phone = %s;
                    """, (client_id, phone_id))
        try:
            conn.commit()
            print("Номер успешно удален.")
        except (Exception, Error) as error:
            print("Ошибка при работе с PostgreSQL", error)
            print("Ошибка. Номер не удален.")
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        print("Такой телефон или клиент отсутствуют в базе данных. Проверьте корректность ввода.")
    return


def update_data(cur, client_id, old_data, new_data):
    try:
        cur.execute("""
        UPDATE clients SET name=%s
        WHERE client_id=%s;
        """, (new_data, client_id))

        cur.execute("""
        UPDATE clients SET surname=%s
        WHERE client_id=%s;
        """, (new_data, client_id))

        cur.execute("""
        UPDATE clients SET email=%s
        WHERE client_id=%s;
        """, (new_data, client_id))
        for phone in old_data.split(', '):
            cur.execute("""
            UPDATE phones SET phone=%s
            WHERE client_id=%s;
            """, (new_data, client_id))

            print(f"Данные пользователя {client_id} заменены. ")
            conn.commit()

    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)


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


def find_client(cur, data):
    cur.execute("""
    SELECT c.client_id, name, surname, email, phone 
    FROM clients c
    LEFT JOIN phones p ON c.client_id = p.client_id
    WHERE name = %s OR surname = %s OR email = %s OR phone = %s;
    """, (data.capitalize(), data.capitalize(), data, data))
    try:
        for client in (clients := cur.fetchall()):
            info = [(id := client[0]),
                    client[1],
                    client[2],
                    client[3],
                    client[4]]
            phones = (', '.join([client[4] for client in clients if client[0] == id and client[4] is not None]))
            print(f"""
            id: {id}, 
            name: {info[1].capitalize()}, 
            surname: {info[2].capitalize()}, 
            email: {info[3]},
            phone: {phones if phones != '' else "Нет номеров для данного клиента."}
            """)
            # how to print once with client_id?
            return info
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        return


# print(f"""
#                 id: {(id := client[0])},
#                 name: {client[1]},
#                 surname: {client[2]},
#                 email: {client[3]},
#                 phone: {', '.join([client[4] for client in clients if client[0] == id])}
#                 """)

def delete_tables(cur):
    try:
        cur.execute("""
        DROP TABLE phones;
        DROP TABLE clients;
        """)
        conn.commit()
        print('Таблицы удалены.')
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
        # psycopg2.errors.UndefinedTable: ОШИБКА:  таблица "phones" не существует
        print("Таблицы не были созданы или уже удалены.")
    return


def exit_db(conn):
    try:
        conn.close()
        print('Вы вышли из базы данных. Для работы перезапустите программу. ')
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)


if __name__ == '__main__':
    user = User()
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
                    8. завершить работу с базой данных.
                    9. удалить таблицы и очистить базу данных.
                    """)
            while True:
                command = input("Введите номер команды: ")
                if command == '1':
                    create_tables(cur)
                elif command == '2':
                    name = input("Введите имя: ")
                    surname = input("Введите фамилию: ")
                    email = input("Введите email: ")
                    email = validate_mail(email)
                    while email is None:
                        email = input("Введите email: ")
                        email = validate_mail(email)
                    print("Введите ниже через запятую номера телефонов клиента")
                    numbers = input("Введите номер(-а) телефона c +7...: ").replace(' ', '').split(',')
                    phones = [phone for number in numbers if (phone := validate_phone(number)) is not None]
                    add_client(cur, name, surname, email, phones)
                elif command == '3':
                    client_id = int(input('Введите id клиента: '))
                    new_phone = input('Введите номер телефона: ')
                    new_phone = validate_phone(new_phone)
                    if new_phone is not None:
                        add_phone(cur, client_id, new_phone)
                    else:
                        print("Номер не валиден и не будет добавлен в базу данных.")
                elif command == '4':
                    client_id = int(input('Введите id клиента: '))
                    data = input('Введите данные, которые хотите изменить: ')
                    old_data = find_client(cur, data)
                    # get list of client_info in return
                    new_data = input('Введите новые данные: ')
                    if data in old_data:
                        update_data(cur, client_id, old_data, new_data)
                    else:
                        print("Клиент с такими данными не найден.")
                elif command == '5':
                    client_id = int(input('Введите id клиента: '))
                    phone = input('Введите номер телефона для удаления: ')
                    phone = validate_phone(phone)
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
                    exit_db(conn)
                elif command == '9':
                    delete_tables(cur)
                else:
                    print('Ошибочная команда, введите команду снова.')

# Ниже закомментированный код для проверки работы функций:
#             # создать структуру БД (таблицы).
#             create_tables(cur)
#             # добавить нового клиента.
#             add_client(cur, name='Anna', surname='Mass', email='lotus@mail.ru',
#                        phones=[validate_phone(phone) for phone in ('+79264839584', '+79485739485')])
#             add_client(cur, name='Dmitriy', surname='Demidov', email='dim@gmail.com',
#                        phones=[validate_phone(phone) for phone in ('375940', '+7 (938) 385 39 58')])
#             # добавить телефон для существующего клиента.
#             add_phone(cur, client_id=2, phone=validate_phone('+7 958 394 85 93'))
#             # изменить данные о клиенте.
#             update_data(cur, 2, )
#             # удалить телефон для существующего клиента.
#             delete_phone(cur, client_id=1, phone=validate_phone('+74059384950'))
#             delete_phone(cur, client_id=2, phone=validate_phone('+7 958 394 85 93'))
#             # удалить существующего клиента.
#             delete_client(cur, client_id=2)
#             # найти клиента по его данным: имени, фамилии, email или телефону.
#             find_client(cur, 'Mass')
#             find_client(cur, '+7 (938) 385 39 58')
#             # завершить работу с базой данных.
#             exit_db(conn)
#             # удалить таблицы и очистить базу данных.
#             delete_tables(cur)
