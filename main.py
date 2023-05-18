import psycopg2
from email_validator import validate_email
import phonenumbers
import os
from dotenv import load_dotenv, find_dotenv


class User:

    def __init__(self):
        load_dotenv(find_dotenv())
        self.db_name = os.getenv('db_name')
        self.user = os.getenv('user')
        self.password = os.getenv('password')


def create_tables(user):
    with psycopg2.connect(database=user.db_name, user=user.user, password=user.password) as conn:
        with conn.cursor() as cur:
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
            except Exception:
                print('Ошибка! Таблицы не созданы!')
    conn.close()
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
    except Exception:
        print(f'Номер {phone} не существует. Попытайтесь ввести номер заново с помощью команды "3".')
        phone = None
        return phone


def add_client(user, name, surname, email, phones=None):
    with psycopg2.connect(database=user.db_name, user=user.user, password=user.password) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                        INSERT INTO clients(name, surname, email) 
                             VALUES (%s, %s, %s) 
                          RETURNING client_id;
            """, (name, surname, email))
            try:
                print("Готово! Id клиента: ", client_id := cur.fetchone()[0])
            except Exception:
                print("Ошибка добавления клиента в Базу данных.")
            for phone in phones:
                cur.execute("""
                INSERT INTO phones(client_id, phone)
                     VALUES (%s, %s)
                  RETURNING phone_id;
                """, (client_id, phone))
                try:
                    print(f"Телефон {phone} добавлен для клиента {client_id}, id: {cur.fetchone()[0]}")
                except psycopg2.errors:
                    print(f"Ошибка добавления телефона {phone} в Базу данных: нет пользователя с id {client_id}.")
    conn.close()
    return


def add_phone(user, client_id, phone):
    with psycopg2.connect(database=user.db_name, user=user.user, password=user.password) as conn:
        with conn.cursor() as cur:
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
    conn.close()
    return


def delete_phone(user, client_id, phone):
    with psycopg2.connect(database=user.db_name, user=user.user, password=user.password) as conn:
        with conn.cursor() as cur:
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
                             WHERE phone_id = %s;
                            """, (phone_id, ))
                try:
                    conn.commit()
                    print("Номер успешно удален.")
                except Exception:
                    print("Ошибка. Номер не удален.")
            except Exception:
                print("Такой телефон или клиент отсутствуют в базе данных. Проверьте корректность ввода.")
    conn.close()
    return


def update_data(user, client_id, data):
    with psycopg2.connect(database=user.db_name, user=user.user, password=user.password) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                UPDATE clients SET 
                """)


def delete_client(user, client_id):
    with psycopg2.connect(database=user.db_name, user=user.user, password=user.password) as conn:
        with conn.cursor() as cur:
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
            except psycopg2.errors.UndefinedColumn:
                print(f"Клиент не удален.")
    conn.close()
    return


def find_client(user, data):
    with psycopg2.connect(database=user.db_name, user=user.user, password=user.password) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT c.client_id, name, surname, email, phone 
            FROM clients c
            LEFT JOIN phones p ON c.client_id = p.client_id
            WHERE name = %s OR surname = %s OR email = %s OR phone = %s;
            """, (data, data, data, data))
            for client in (clients := cur.fetchall()):
                info = [(id := client[0]),
                        client[1],
                        client[2],
                        client[3],
                        ', '.join([client[4] for client in clients if client[0] == id])]
                print(f"""
                id: {id}, 
                name: {info[1]}, 
                surname: {info[2]}, 
                email: {info[3]},
                phone: {info[4]}
                """)
                # how to print once with client_id?
    conn.close()
    return info

# print(f"""
#                 id: {(id := client[0])},
#                 name: {client[1]},
#                 surname: {client[2]},
#                 email: {client[3]},
#                 phone: {', '.join([client[4] for client in clients if client[0] == id])}
#                 """)

def delete_tables(user):
    with psycopg2.connect(database=user.db_name, user=user.user, password=user.password) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            DROP TABLE phones;
            DROP TABLE clients;
            """)
            conn.commit()
    conn.close()
    print('Таблицы удалены.')
    return


def manage_program(user):
    print("""
        Доступные команды:
        1. создать структуру БД (таблицы).
        2. добавить нового клиента.
        3. добавить телефон для существующего клиента.
        4. изменить данные о клиенте.
        5. удалить телефон для существующего клиента.
        6. удалить существующего клиента.
        7. найти клиента по его данным: имени, фамилии, email или телефону.
        8. удалить таблицы и очистить базу данных.
        """)
    while True:
        command = input("Введите номер команды: ")
        if command == '1':
            create_tables(user)
        elif command == '2':
            name = input("Введите имя: ")
            surname = input("Введите фамилию: ")
            email = input("Введите email: ")
            email = validate_mail(email)
            while email is None:
                email = input("Введите email: ")
                email = validate_mail(email)
            print("Введите ниже через запятую номера телефонов клиента")
            numbers = input("Введите номер(-а) телефона: ").replace(' ', '').split(',')
            phones = [phone for number in numbers if (phone := validate_phone(number)) is not None]
            add_client(user, name, surname, email, phones)
        elif command == '3':
            client_id = int(input('Введите id клиента: '))
            new_phone = input('Введите номер телефона: ')
            new_phone = validate_phone(new_phone)
            if new_phone is not None:
                add_phone(user, client_id, new_phone)
            else:
                print("Номер не валиден и не будет добавлен в базу данных.")
        elif command == '4':
            client_id = int(input('Введите id клиента: '))
            data = input('Введите данные, которые хотите изменить: ')
            old_data = find_client(user, client_id, data)
            # get list of client_info in return
            if data in old_data:
                update_data(user, client_id, data)
            else:
                print("Клиент с такими данными не найден.")
        elif command == '5':
            client_id = int(input('Введите id клиента: '))
            phone = input('Введите номер телефона для удаления: ')
            phone = validate_phone(phone)
            delete_phone(user, client_id, phone)
        elif command == '6':
            client_id = int(input('Введите id клиента для удалениия: '))
            delete_client(user, client_id)
        elif command == '7':
            # name = input('Введите имя клиента: ')
            # surname = input("Введите фамилию: ")
            # email = input("Введите email: ")  # is valid + normalize
            # email = validate_mail(email)
            # phone = input('Введите номер телефона: ')  # is valid + to format
            # phone = validate_phone(phone)
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
            find_client(user, data)
        elif command == '8':
            delete_tables(user)
        else:
            print('Ошибочная команда, введите команду снова.')


if __name__ == '__main__':
    user = User()
    manage_program(user)


    # Ниже закомментированный код для проверки работы функций:


