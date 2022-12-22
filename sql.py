import pymysql


# from REG_to_APPLY import Registration_sadik


class Database:
    def __init__(self):
        self.conn = pymysql.connect(
            user='root',
            password='ntygazRPNautoz',
            host='127.0.0.1',
            port=3308,
            database='knm'
        )
    def take_request_from_database(self, request: str = """SHOW DATABASES;"""):
        with self.conn.cursor() as cursor:
            cursor.execute(request)
            result = cursor.fetchall()
            return result

    def commit(self):
        self.conn.commit()

    def create_json_formate_knm_in_raw_knm(self, id, kind, type, status, year, start_date, stop_date, inn, ogrn, risk, object_kind, controll_organ, data):
        with self.conn.cursor() as cursor:
            insert = f"""INSERT INTO erknm (id, kind, type, status, year, start_date, stop_date, inn, ogrn, risk, object_kind, controll_organ, data) VALUES('{id}', '{kind}', '{type}', '{status}', '{year}', '{start_date}', '{stop_date}', '{inn}', '{ogrn}', '{risk}', '{object_kind}', '{controll_organ}', '{data}') ON DUPLICATE KEY UPDATE status='{status}', data='{data}';"""
            cursor.execute(insert)
            self.conn.commit()

    def change_stop_date_by_erpID(self, stop_date, erpID,):
        """

        @param stop_date:  новая дата в формате "гггг-мм-дд"
        @param erpID: id проверки в базе данных в таблице erknm
        @return:
        """
        with self.conn.cursor() as cursor:
            update = f"""UPDATE erknm SET stop_date='{stop_date}' WHERE id={erpID};"""
            cursor.execute(update)
            self.conn.commit()

    def ultra_create_handler(self, result):

        with self.conn.cursor() as cursor:
            # вносим теруправление

            controllingOrganization = result['controllingOrganization']
            controllingOrganizationId = result['controllingOrganizationId']
            district = result['district']
            cursor.execute(
                f"""SELECT id FROM knd_terr_upravlenie WHERE controllingOrganizationId='{controllingOrganizationId}';""")
            exists_terr_uprav = cursor.fetchall()
            if exists_terr_uprav == ():
                cursor.execute(
                    f"""INSERT INTO knd_terr_upravlenie(name, controllingOrganizationId, district) VALUES 
                                ("{controllingOrganization}", {controllingOrganizationId}, "{district}")""")
                # self.conn.commit()
                cursor.execute("SELECT LAST_INSERT_ID();")
                terr_upr_id = cursor.fetchall()[0][0]

            else:
                terr_upr_id = exists_terr_uprav[0][0]


            # вносим проверку

            inspection_number = result['erpId']
            status = result['status']
            profilactic = result['isPm']
            if profilactic is True:
                profilactic = 1
            else:
                profilactic = 0

            print(inspection_number)

            comment = result['comment']
            print(comment)
            if not comment:
                comment = ""
            else:
                comment = comment.replace("'", "").replace('"', '').replace("   ", " ").replace("  ", " ").replace('/"', ' ')
            print('контрольная точка 0')
            plan_id = result['planId']
            if not plan_id:
                plan_id = 0

            date_end = result['stopDateEn']
            if date_end is None:
                date_end = '1900-01-01'

            knm_id = result['id']
            cursor.execute(f"""SELECT id FROM knd_inspection WHERE knm_id='{knm_id}';""")
            res = cursor.fetchall()
            print('контрольная точка 01')
            if res == ():
                cursor.execute(f"""INSERT INTO knd_inspection 
                (knm_id, kind, profilactic, date_start, mspCategory, number, status, year, terr_upr_id, comment, plan_id, date_end, desicion_number, desicion_date, last_inspection_date_end)
                VALUES 
                ("{knm_id}", "{result['kind']}", "{profilactic}", "{result['startDateEn']}", "{result['mspCategory']}", "{inspection_number}",
                 "{status}", "{result['year']}", "{terr_upr_id}", "{comment}", "{plan_id}", "{date_end}", "0", "1900-01-01", "1900-01-01");""")

                # self.conn.commit()
                cursor.execute("SELECT LAST_INSERT_ID();")
                inspection_id = cursor.fetchall()[0][0]
            else:
                inspection_id = res[0][0]
                cursor.execute(f"""UPDATE knd_inspection SET 
                    status='{status}', comment='{comment}' WHERE id={inspection_id};""")
                # self.conn.commit()

            print('контрольная точка 1')


            count_inn = len(result['organizationsInn'])
            if count_inn == 1:
                # внесение субъекта, если это не рейд
                subject_name = result['organizationName']
                address = result['addresses'][0]
                inn = result['inn']
                ogrn = result['inn']

                cursor.execute(f"""SELECT id FROM knd_subject WHERE inn='{inn}';""")
                res = cursor.fetchall()
                if res == ():
                    cursor.execute(f"""INSERT INTO knd_subject(name, address, inn, ogrn, e_mail, district) VALUES (
                                '{subject_name}', '{address}', '{inn}', '{ogrn}', ' ', ' ');""")
                    # self.conn.commit()
                    cursor.execute("SELECT LAST_INSERT_ID();")
                    subject_id = cursor.fetchall()[0][0]
                else:
                    subject_id = res[0][0]


                # внесение объекта, если это не рейд
                objects_adresses = result['addresses']
                objects_kinds = result['objectsKind']
                objects_risks = result['riskCategory']
                for address, kind, risk in zip(objects_adresses, objects_kinds, objects_risks):
                    cursor.execute(
                        f"""SELECT id FROM knd_object WHERE subject_id='{subject_id}' AND address='{address}' AND risk='{risk}' AND kind='{kind}';""")
                    res = cursor.fetchall()
                    if res == ():
                        cursor.execute(
                            f"""INSERT INTO knd_object(subject_id, kind, address, risk) VALUES ('{subject_id}', '{kind}', '{address}', '{risk}');""")
                        # self.conn.commit()
                        cursor.execute("SELECT LAST_INSERT_ID();")
                        object_id = cursor.fetchall()[0][0]
                    else:
                        object_id = res[0][0]

                    # создаем M_to_m_insp_obj
                    cursor.execute(
                        f"""SELECT id FROM knd_m_to_m_object_inspection WHERE object_id='{object_id}' AND inspection_id='{inspection_id}';""")
                    res = cursor.fetchall()
                    if res == ():
                        cursor.execute(
                            f"""INSERT INTO knd_m_to_m_object_inspection(inspection_id, object_id) VALUES ('{inspection_id}', '{object_id}')""")





            else:
                # внесение субъекта, если это рейд
                risk = result['objectsKind'][0]
                kind = result['objectsKind'][0]
                for subject_name, inn, ogrn in zip(result['organizationsName'], result['organizationsInn'],
                                                   result['organizationsOgrn']):
                    cursor.execute(f"""SELECT id FROM knd_subject WHERE inn='{inn}';""")
                    res = cursor.fetchall()
                    if res == ():
                        cursor.execute(f"""INSERT INTO knd_subject(name, address, inn, ogrn, e_mail, district) VALUES (
                                                    '{subject_name}', ' ', '{inn}', '{ogrn}', ' ', ' ');""")
                        # self.conn.commit()
                        cursor.execute("SELECT LAST_INSERT_ID();")
                        subject_id = cursor.fetchall()[0][0]
                    else:
                        subject_id = res[0][0]

                    #  и сразу же создаем объект
                    cursor.execute(
                        f"""SELECT id FROM knd_object WHERE subject_id='{subject_id}' AND risk='{risk}' AND kind='{kind}';""")
                    res = cursor.fetchall()
                    if res == ():
                        cursor.execute(
                            f"""INSERT INTO knd_object(subject_id, kind, address, risk) VALUES ('{subject_id}', '{kind}', ' ', '{risk}');""")
                        # self.conn.commit()
                        cursor.execute("SELECT LAST_INSERT_ID();")
                        object_id = cursor.fetchall()[0][0]
                    else:
                        object_id = res[0][0]

                    # создаем M_to_m_insp_obj
                    cursor.execute(
                        f"""SELECT id FROM knd_m_to_m_object_inspection WHERE object_id='{object_id}' AND inspection_id='{inspection_id}';""")
                    res = cursor.fetchall()
                    if res == ():
                        cursor.execute(
                            f"""INSERT INTO knd_m_to_m_object_inspection(inspection_id, object_id) VALUES ('{inspection_id}', '{object_id}')""")
            self.conn.commit()


    def create_terr_upr_returned_id(self, name, controllingOrganizationId, district):
        with self.conn.cursor() as cursor:

            cursor.execute(f"""SELECT id FROM knd_terr_upravlenie WHERE controllingOrganizationId='{controllingOrganizationId}';""")
            exists_terr_uprav = cursor.fetchall()
            if exists_terr_uprav == ():
                cursor.execute(
                    f"""INSERT INTO knd_terr_upravlenie(name, controllingOrganizationId, district) VALUES 
                    ("{name}", {controllingOrganizationId}, "{district}")""")
                self.conn.commit()
                cursor.execute("SELECT LAST_INSERT_ID();")
                res_id = cursor.fetchall()[0][0]

            else:
                res_id = exists_terr_uprav[0][0]
            return res_id

    def create_inspection_knd_returned_id(self, knm_id: int,  kind: str, profilactic: bool,
                                          date_start: str, mspCategory: str, number: str,
                                          status: str, comment: str, year: int, terr_upr_id: int,
                                          plan_id: int, date_end: str, last_inspection_date_end):




        with self.conn.cursor() as cursor:
            cursor.execute(f"""SELECT id FROM knd_inspection WHERE knm_id='{knm_id}';""")
            result = cursor.fetchall()
            if result == ():
                cursor.execute(f"""INSERT INTO knd_inspection 
                (knm_id, kind, profilactic, date_start, mspCategory, number, status, year, terr_upr_id, comment, plan_id, date_end, desicion_number, desicion_date, last_inspection_date_end)
                VALUES 
                ("{knm_id}", "{kind}", "{profilactic}", "{date_start}", "{mspCategory}", "{number}",
                 "{status}", "{year}", "{terr_upr_id}", "{comment}", "{plan_id}", "{date_end}", "0", "1900-01-01", "{last_inspection_date_end}");""")

                self.conn.commit()
                cursor.execute("SELECT LAST_INSERT_ID();")
                insp_id = cursor.fetchall()[0][0]
            else:
                insp_id = result[0][0]
                cursor.execute(f"""UPDATE knd_inspection SET 
                    status='{status}', comment='{comment}' WHERE id={insp_id};""")
                self.conn.commit()
            return insp_id

    def create_subject_with_returned_id(self, name, address, inn, ogrn, e_mail, district):
        with self.conn.cursor() as cursor:
            cursor.execute(f"""SELECT id FROM knd_subject WHERE inn='{inn}';""")
            result = cursor.fetchall()
            if result == ():
                cursor.execute(f"""INSERT INTO knd_subject(name, address, inn, ogrn, e_mail, district) VALUES (
                '{name}', '{address}', '{inn}', '{ogrn}', '{e_mail}', '{district}');""")
                self.conn.commit()
                cursor.execute("SELECT LAST_INSERT_ID();")
                subject_id = cursor.fetchall()[0][0]
            else:
                subject_id = result[0][0]
            return subject_id

    def create_object_with_returned_id(self, subject, kind, address, risk):
        with self.conn.cursor() as cursor:
            cursor.execute(f"""SELECT id FROM knd_object WHERE subject_id='{subject}' AND risk='{risk}' AND kind='{kind}';""")
            result = cursor.fetchall()
            if result == ():
                cursor.execute(f"""INSERT INTO knd_object(subject_id, kind, address, risk) VALUES ('{subject}', '{kind}', '{address}', '{risk}');""")
                self.conn.commit()
                cursor.execute("SELECT LAST_INSERT_ID();")
                object_id = cursor.fetchall()[0][0]
            else:
                object_id = result[0][0]
            return object_id



    def exists_table(self, table_name):
        with self.conn.cursor() as cursor:
            cursor.execute(f"SHOW TABLES LIKE '{table_name}';")
            result = cursor.fetchall()
            if result == ():
                return True
            return False
        
        
    def get_terr_upravlenie_name(self, condition):
        with self.conn.cursor() as cursor:
            cursor.execute(f"SELECT name FROM knd_terr_upravlenie WHERE name='{condition}';")
            result = cursor.fetchall()
            return result

    def get_terr_upravlenie_id(self, condition):
        with self.conn.cursor() as cursor:
            cursor.execute(f"SELECT id FROM knd_terr_upravlenie WHERE name='{condition}';")
            result = cursor.fetchall()
            if result != ():
                return result[0][0]
            else:
                return result

    def get_plan_proverok_id(self, condition):
        with self.conn.cursor() as cursor:
            cursor.execute(f"SELECT id FROM knd_plan_proverok WHERE number='{condition}';")
            result = cursor.fetchall()
            if result != ():
                return result[0][0]
            else:
                return result



    def get_kind_inspection_id(self, condition):
        with self.conn.cursor() as cursor:
            cursor.execute(f"SELECT id FROM knd_kind_inspection WHERE kind='{condition}';")
            result = cursor.fetchall()
            if result != ():
                return result[0][0]
            else:
                return result

    def get_inspection_id(self, condition):
        with self.conn.cursor() as cursor:
            cursor.execute(f"SELECT id FROM knd_inspection WHERE number='{condition}';")
            result = cursor.fetchall()
            if result != ():
                return result[0][0]
            else:
                return result

    def insert_plan_proverok(self, ter_upr, number, year, count, status):
        with self.conn.cursor() as cursor:
            cursor.execute(
                f"""INSERT INTO knd_plan_proverok(ter_upr_id, number, year, count, status) VALUES ('{ter_upr}', '{number}', '{year}', '{count}', '{status}')""")
            self.conn.commit()

    def insert_terr_uprav(self, name, controllingOrganizationId):
        with self.conn.cursor() as cursor:
            cursor.execute(f"""INSERT INTO knd_terr_upravlenie(name, controllingOrganizationId) VALUES ('{name}', '{controllingOrganizationId}')""")
            self.conn.commit()

    def insert_subject_with_return_id(self, name, address, inn, ogrn):
        with self.conn.cursor() as cursor:
            cursor.execute(
                f"""INSERT INTO knd_subject(name, address, e_mail, district, inn, ogrn) VALUES ('{name}', '{address}', '""', '""', '{inn}', '{ogrn}')""")
            self.conn.commit()
            cursor.execute(f"""SELECT LAST_INSERT_ID();""")
            result = cursor.fetchall()
            if result != ():
                return result[0][0]
            else:
                return result

    def insert_terr_upr_with_return_id(self, name, controllingOrganizationID):
        with self.conn.cursor() as cursor:
            cursor.execute(f"SELECT id FROM knd_terr_upravlenie WHERE controllingOrganizationId='{controllingOrganizationID}';")
            result = cursor.fetchall()
            if result != ():
                return result[0][0]
            else:
                cursor.execute(
                    f"""INSERT INTO knd_terr_upravlenie(name, controllingOrganizationId) VALUES ('{name}', '{controllingOrganizationID}')""")
                self.conn.commit()
                cursor.execute(f"""SELECT LAST_INSERT_ID();""")
                result = cursor.fetchall()

                return result[0][0]


    def insert_object_with_return_id(self, subject_id, kind, address, risk_id):
        with self.conn.cursor() as cursor:
            cursor.execute(
                f"""INSERT INTO knd_object(subject_id, kind, address, risk_id) VALUES ('{subject_id}', '{kind}', '{address}', '{risk_id}')""")
            self.conn.commit()

            cursor.execute(f"""SELECT LAST_INSERT_ID();""")
            result = cursor.fetchall()
            if result != ():
                return result[0][0]
            else:
                return result

    def insert_inspection_with_return_id(self, plan_id: int, kind_id: int, number):
        with self.conn.cursor() as cursor:
            cursor.execute(
                f"""INSERT INTO knd_inspection(plan_id, kind_id, number) VALUES ('{plan_id}', '{kind_id}', '{number}')""")
            self.conn.commit()

            cursor.execute(f"""SELECT LAST_INSERT_ID();""")
            result = cursor.fetchall()
            if result != ():
                return result[0][0]
            else:
                return result

    def insert_m_to_m_object_inspection(self, inspection_id, object_id):
        with self.conn.cursor() as cursor:
            cursor.execute(f"""SELECT id FROM knd_m_to_m_object_inspection WHERE object_id='{object_id}' AND inspection_id='{inspection_id}';""")
            result = cursor.fetchall()
            if result == ():
                cursor.execute(
                    f"""INSERT INTO knd_m_to_m_object_inspection(inspection_id, object_id) VALUES ('{inspection_id}', '{object_id}')""")
                self.conn.commit()


    def find_risk_id(self, condition):
        with self.conn.cursor() as cursor:
            cursor.execute(f"SELECT id FROM knd_risk_category WHERE category='{condition}';")
            result = cursor.fetchall()
            if result != ():
                return result[0][0]
            else:
                return result

    def change_names_knd_terr_upravlenie(self, terr_id, new_name):
        with self.conn.cursor() as cursor:
            cursor.execute(f"UPDATE knd_terr_upravlenie SET name='{new_name}' where id={terr_id}")
            self.conn.commit()

    def get_connect(self):

        rang = self.get_info()

        # print(rang[0][12])
        # self.listrang(rang)
        self.raspred(rang)
        # self.get_sadik_info(31)

    def raspred(self, rang):
        ready = []
        applied = []
        registred = []
        list = {'ready': {'conteiner': ready, 'function': 'будем согласовывать'},
                'applied': {'conteiner': applied, 'function': 'будем регистрировать'},
                'registred': {'conteiner': registred, 'function': 'будем отправлять'}}
        for o in rang:
            status = o[11]
            for k, v in list.items():
                if status == k:
                    print(f'{v["function"]}  {o[3]}')
                    v["conteiner"].append(o)
        print(f'ready {ready}')
        print(f'applied {applied}')
        print(f'registred {registred}')
        for i in ready:
            print(i)

    def listrang(self, rang):
        for o in rang:
            id_o = o[0]
            groups = o[1]
            group_size = o[2]
            date_start = o[3]
            date_end = o[4]
            reason = o[5]
            fio_covid = o[6]
            fio_post = o[7]
            last_day = o[8]
            identify_day = o[9]
            address_spe = o[10]
            status = o[11]
            sadik_id = o[14]

            sadik = self.get_sadik_info(sadik_id)
            # print(sadik[0])
            id_s = sadik[0][0]
            district = sadik[0][1]
            properties = sadik[0][2]
            only_name = sadik[0][3]
            address = sadik[0][4]
            fio_director = sadik[0][5]
            e_mail = sadik[0][6]
            inn = sadik[0][7]
            ogrn = sadik[0][8]
            sed_name = sadik[0][9]

            print(o)

            # self.level_up_status(id_o, status)

    def get_sadik_info(self, sadik_id):
        with self.conn.cursor() as cursor:
            cursor.execute(f"Select * FROM sadidi_sadik where id='{sadik_id}'")
            result = cursor.fetchall()
            return result

    # def get_info(self):
    #     # self.cursor.execute("Select * FROM sadidi_ordinary where status='ready'")
    #     with self.conn.cursor() as cursor:
    #         cursor.execute("Select * FROM sadidi_ordinary")
    #         result = cursor.fetchall()
    #         return result

    def level_up_status(self, id, status):
        referense = {'ready': 'applied', 'applied': 'registred', 'registred': 'sended', 'sended': 'ready'}
        # print(referense)
        if status == 'sended':
            return
        with self.conn.cursor() as cursor:
            for r in referense:
                if status == r:
                    # print(f'Новый статус:  {referense[r]}')
                    cursor.execute(f"UPDATE sadidi_ordinary SET status='{referense[r]}' where id={id}")
                    self.conn.commit()
                    return

    def assign_number(self, id, number):
        with self.conn.cursor() as cursor:
            cursor.execute(f"UPDATE sadidi_ordinary SET doc_number='{number}' where id={id}")
            self.conn.commit()
            return

    def get_current_date_ordinaries(self, district):
        with self.conn.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM sadidi_ordinary WHERE date_end >= CURRENT_DATE() AND sadik_id = ANY (SELECT id FROM sadidi_sadik WHERE district='{district}')")
            result = cursor.fetchall()
            return result

    def user_info(self, district):
        with self.conn.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM sadidi_ordinary WHERE date_end >= CURRENT_DATE() AND sadik_id = ANY (SELECT id FROM sadidi_sadik WHERE district='{district}')")
            result = cursor.fetchall()
            return result


if __name__ == "__main__":
    Database()
