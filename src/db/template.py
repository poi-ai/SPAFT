import traceback

class Template():
    '''DB�᥽�åɤΥƥ�ץ졼��,�ɤ������ƤФ�ʤ����ƤФ�Ƥ�ư���ʤ�'''
    def __init__(self, log):
        self.log = log

    def select_tablename(self):
        '''
        SELECT

        Args:

        Returns:
        '''
        try:
            # cursor�ΰ�����ʤ����ȥ��ץ���֤�
            with self.conn.cursor(self.dict_return) as cursor:
                sql = ''''
                    SELECT
                        xx
                    FROM
                        xx
                    WHERE
                        xx
                '''

                cursor.execute(sql)

                # 1�Ԥ���ȴ���Ф�
                #row = cursor.fetchone()
                # �����ʤ�,�ǡ����ʤ� -> None
                # �����ʤ�,�ǡ������� -> tuple
                # pymysql.cursors.DictCursor,�ǡ����ʤ� -> None
                # pymysql.cursors.DictCursor,�ǡ������� -> dict


                # ����ȴ���Ф�
                rows = cursor.fetchall()
                # �����ʤ�,�ǡ����ʤ� -> ��tuple
                # �����ʤ�,�ǡ���1�� -> tuple
                # �����ʤ�,�ǡ���ʣ���� -> tuple(tuple,tuple,...)
                # pymysql.cursors.DictCursor,�ǡ����ʤ� -> ��tuple
                # pymysql.cursors.DictCursor,�ǡ���1�� -> list[dict]
                # pymysql.cursors.DictCursor,�ǡ���ʣ���� -> list[dict,dict,...]

                # ���ꤷ���Կ�ȴ���Ф�
                num = 100
                rows = cursor.fetchmany(num)
                # fetchall��Ʊ
        except Exception as e:
            self.log.error('xx�ǥ��顼', e, traceback.format_exc())
            return False

    def insert_tablename(self):
        '''
        INSERT

        Args:

        Returns:
        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    INSERT INTO xxx
                    (
                        aaa,
                        bbb,
                        num
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )
                '''

                    # �ץ졼���ۥ������int�Ǥ�str�Ǥ��������Ƥ����ΤǤȤꤢ����%s�ˤ��Ȥ����ɤ�

                cursor.execute(sql, (
                    'huga',
                    '77',
                    100,
                ))

            return True
        except Exception as e:
            self.log.error('xxx�ؤ�INSERT�ǥ��顼', e, traceback.format_exc())
            return False

    def update_tablename(self):
        '''
        UPDATE

        Args:

        Returns:

        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    UPDATE
                        xx
                    SET
                        xx = %s,
                        xx = %s
                    WHERE
                        xx = %s
                '''

                cursor.execute(sql, (
                    'hoge',
                    77
                ))

            return True
        except Exception as e:
            self.log.error(f'xx��UPDATE�ǥ��顼', e, traceback.format_exc())
            return False

    def delete_tablename(self):
        '''
        DELETE

        Args:

        Returns:

        '''
        try:
            with self.conn.cursor() as cursor:
                sql = '''
                    DELETE FROM
                        xx
                    WHERE
                        xx = %s
                '''

                cursor.execute(sql, (
                    'hoge'
                ))

            return True
        except Exception as e:
            self.log.error(f'xx��DELETE�ǥ��顼', e, traceback.format_exc())
            return False


    def sample_transaction(self):
        '''
        Transaction

        Args:

        Returns:
        '''
        with self.conn.cursor() as cursor:

            # self.start_transaction()

            # INSERT �ɲä���ǡ����ȥ��������������Ϥ�
            # result = self.insert_test(data, cursor)

            # UPDATE ��������ǡ����Ȥ����Ȥ����������������Ϥ�
            # result = self.update_test(data, conditions, cursor)

            # UPDATE ���������Ȥ����������������Ϥ�
            # result = self.delete_test(data, cursor)

            # ���줾��ν�������֤��ͤǼ¹Է�̤������ä� ���ߥåȤ�����Хå���
            # if result:
            #     self.commit()
            # else:
            #     self.rollback()

            # SQL�¹Է�̤�self.transaction_flag���ͤù�������
            # self.end_transaction()
            # �Ǥ�褤
            pass

        return True