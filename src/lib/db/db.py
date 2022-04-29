import mysql.connector
from mysql.connector import Error

HOST = '54.37.129.120'
PORT = 3306
USER = 'pepega'
PASSWORD = 'hRLxsXQwk0REGuf2'
DATABASE = 'plasmo_rp'
debug = True

'''conn = pymysql.connect(host=HOST,
                       port=PORT,
                       user=USER,
                       passwd=PASSWORD,
                       db=DATABASE)
'''


def create_connection(host_name, user_name, user_password):
    connection = None

    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database='plasmo_rp',
            use_pure=True
        )
        print("Connection to MySQL DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection


def recon():
    global conn
    conn = create_connection(HOST, USER, PASSWORD)


recon()


def requestdb(request: str, retry=False):
    try:
        cur = conn.cursor(buffered=True)
        cur.execute(request)
        resp = cur.fetchall()
        cur.close()
        if debug:
            print(request, resp)
        return resp
    except IndexError:
        return None
    except Exception as err:
        print(err)
        recon()
        if not retry:
            return requestdb(request, retry=True)
        else:
            return None


def select(table='parliament_votes', columns='*', where='', args='', always_return_all=False, return_list=False,
           return_matrix=False, retry=False):
    try:
        if where != '' and not 'WHERE' in where:
            where = 'WHERE ' + where
        request = f'SELECT {columns} FROM {table} {where} {args}'
        if debug:
            print(request)
        cur = conn.cursor(buffered=True)
        cur.execute(request)
        fetchall = cur.fetchall()
        cur.close()

        if return_list:
            response = []
            if len(fetchall):
                for elem in fetchall:
                    response.append(elem[0])
                return response
            else:
                return []
        elif return_matrix:
            response = []
            if len(fetchall):
                for elem in fetchall:
                    response.append([elem[1], int(elem[0])])
                print(response)
                return response
            return []
        if len(fetchall) <= 1 and not always_return_all:
            return fetchall[0]
        else:
            return fetchall
    except IndexError:
        return None
    except Exception as err:
        print(err)
        recon()
        if not retry:
            return select(table=table,
                          columns=columns,
                          where=where,
                          args=args,
                          always_return_all=always_return_all,
                          return_list=return_list,
                          return_matrix=return_matrix,
                          retry=True)
        else:
            return None


def insert(data, table='parliament_votes', retry=False):
    try:
        request = f'INSERT INTO {table} SET {data}'
        if debug:
            print(request)
        cur = conn.cursor(buffered=True)
        cur.execute(request)
        conn.commit()
        cur.close()
        return True
    except Exception as err:
        print(err)
        recon()
        if not retry:
            return insert(data=data, table=table, retry=True)
        else:
            return None


def delete(where, table='parliament_votes', retry=False):
    try:
        request = f'DELETE FROM {str(table)} WHERE {str(where)}'
        if debug:
            print(request)
        cur = conn.cursor(buffered=True)
        cur.execute(request)
        conn.commit()
        cur.close()
    except Exception as err:
        print(err)
        recon()
        if not retry:
            return delete(where=where, table=table, retry=True)
        else:
            return None


def update(data, where, table='parliament_votes', retry=False):
    try:
        request = f'UPDATE {table} SET {data} WHERE {where}'
        if debug:
            print(request)
        cur = conn.cursor(buffered=True)
        cur.execute(request)
        conn.commit()
        cur.close()
    except Exception as err:
        print(err)
        recon()
        if not retry:
            return update(data=data, where=where, table=table, retry=True)
        else:
            return None