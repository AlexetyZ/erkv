from erknm.sql import Database
from multiprocessing import Pool
import logging
from pathlib import Path
import traceback
from datetime import date
import json
from erknm.knm_status_kinds import completed


logging.basicConfig(format='%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s(%(lineno)d) - %(message)s',
                        filename=f'logging/reports/{date.today().strftime("%d.%m.%Y")}.log', encoding='utf-8',
                        level=logging.INFO)
logger = logging.getLogger(Path(traceback.StackSummary.extract(traceback.walk_stack(None))[0].filename).name)

d = Database()
exception_knm = []

# ter_upr_name = knm['controllingOrganization']
# controllingOrganizationID = knm['controllingOrganizationID']
# ter_upr_name_id = d.insert_terr_upr_with_return_id(name=ter_upr_name, controllingOrganizationID=controllingOrganizationID)


def formattig_str(text):
    text = str(text).replace("'", "").replace('"', '').replace("   ", " ").replace("  ", " ").replace('/"', ' ')
    return text


def create_knm_in_knms(knm):

    # for number, (key, value) in enumerate(knm.items()):
    #     print(key, value)
    terr_upr_id = d.create_terr_upr_returned_id(knm['controllingOrganization'], knm['controllingOrganizationId'], knm['district'])
    try:
        last_inspect_date = knm['reasonsList']['o']['date']
    except:
        last_inspect_date = '1990-01-01'

    desicion_date = knm['approveDocOrderDate']
    if desicion_date is None:
        desicion_date = '1900-01-01'

    date_end = knm['stopDateEn']
    if date_end is None:
        date_end = '1900-01-01'


    comment = str(knm['comment'])
    comment = formattig_str(comment)
    print(comment)

    insp_id = d.create_inspection_knd_returned_id(plan_id=knm['planId'],
                                                  knm_id=knm['id'],
                                                  kind=knm['kind'],
                                                  profilactic=knm['isPm'],
                                                  deleted=knm['deleted'],
                                                  date_start=knm['startDateEn'],
                                                  date_end=date_end,
                                                  desicion_number=knm['approveDocOrderNum'],
                                                  desicion_date=desicion_date,
                                                  last_inspection_date_end=last_inspect_date,
                                                  mspCategory=formattig_str(knm['mspCategory'][0]),
                                                  number=knm['erpId'],
                                                  status=formattig_str(knm['status']),
                                                  comment=comment,
                                                  year=knm['year'],
                                                  terr_upr_id=terr_upr_id)
    address = formattig_str(knm['addresses'][-1])
    # print(address)
    subject_id = d.create_subject_with_returned_id(

        name=formattig_str(knm['organizationName']),
        address=address,
        inn=knm['inn'],
        ogrn=knm['ogrn']
    )
    for address, risk in zip(knm['addresses'], knm['riskCategory']):
        address = formattig_str(address)
        object_id = d.create_object_with_returned_id(
            subject=subject_id,
            kind=formattig_str(knm['objectsKind'][0]),
            address=formattig_str(address),
            risk=formattig_str(risk)
        )
        d.insert_m_to_m_object_inspection(inspection_id=insp_id, object_id=object_id)


def database_inserts_conductor(list_knm: list):
    """
    Функция для внесения списка КНМ в базу данных с обработкой ошибок. Пробует просто запустить функцию и ожидает
        успешного выполнения, при неуспешном - пробует второй раз, но высталяет специальный параметр.
        При повторной неудаче умывает руки и выдает ошибку, с которой не удалось справиться.

    @param list_knm: Список КМН, как правило в формате json (список json-ов) для загрузки в базу данных
    @return:
    """
    logger.info('началась запись в базу данных...')


    for knm in list_knm:

        result = new_insert_in_database(knm)
        if result is False:
            try:
                # result = insert_in_database(knm, special=True)
                result = new_insert_in_database(knm)
                if result is False:
                    logger.info('Возникла ошибка, с которой не удалось справиться...')
                    exception_knm.append(knm)
            except Exception as ex:
                logger.info(f'Непредвиденная ошибка строка 90: {ex}')
                exception_knm.append(knm)
    if exception_knm:
        with open('Exception_knm.json', 'w') as file:
            json.dump(exception_knm, file)
            result = f'По итогу внесения не было внесено {len(exception_knm)} проверок. Они упакованы в файл Exception_knm.json и их ошибки ожидают решений'
            logger.info(result)
        return result
    logger.info('Все проверки успешно занесены!')


def database_inserts_conductor_for_multiprocessing(knm):

    result = new_insert_in_database(knm)
    if result is False:
        try:
            result = new_insert_in_database(knm)
            if result is False:
                logger.info('Возникла ошибка, с которой не удалось справиться...')
                logger.info('')
                exception_knm.append(knm)
        except Exception as ex:
            logger.info(f'Непредвиденная ошибка строка 90: {ex}')
            exception_knm.append(knm)


def multiple_inserts(processes: int, knm_list: list):
    logger.info('старт программы')
    pool = Pool(processes)
    pool.map(database_inserts_conductor_for_multiprocessing, knm_list)
    if exception_knm:
        with open('Exception_knm.json', 'w') as file:
            json.dump(exception_knm, file)
            result = f'По итогу внесения не было внесено {len(exception_knm)} проверок. Они упакованы в файл Exception_knm.json и их ошибки ожидают решений'
            logger.info(result)
        return result
    logger.info('Все проверки успешно занесены!')


def insert_in_database(result: dict, special: bool = False) -> bool:

    try:
        # вносим теруправление
        terr_upr_name = result['controllingOrganization']
        terr_upr_erknm_number = result['controllingOrganizationId']
        terr_upr_district = result['district']

        terr_upr_id = Database().create_terr_upr_returned_id(
            name=terr_upr_name,
            controllingOrganizationId=terr_upr_erknm_number,
            district=terr_upr_district
        )
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
        comment = formattig_str(comment)
        print(comment)
        if not comment:
            comment = ""

        plan_id = result['planId']
        if not plan_id:
            plan_id = 0


        date_end = result['stopDateEn']
        if date_end is None:
            date_end = '1900-01-01'
            if status in completed:
                print('завершенные проверки, не имеющие дату окончания, должны быть приведены в порядок '
                      '- дату нужно найти в сведениях о составлении акта. здесь должна быть система, '
                      'которая передает такие проверки в один список для поиска у них потом даты окончания, '
                      'если передавать непосредственног при обнаружении - будет долго')



        inspection_id = Database().create_inspection_knd_returned_id(
            terr_upr_id=terr_upr_id,
            knm_id=result['id'],
            kind=result['kind'],
            profilactic=profilactic,
            date_start=result['startDateEn'],
            mspCategory=result['mspCategory'],
            number=inspection_number,
            status=status,
            year=result['year'],
            comment=comment,
            plan_id=plan_id,
            date_end=date_end,
            last_inspection_date_end='1900-01-01'
        )

        count_inn = len(result['organizationsInn'])
        if count_inn == 1:
            # внесение субъекта, если это не рейд
            subject_name = result['organizationName']
            address = result['addresses'][0]
            inn = result['inn']
            ogrn = result['inn']

            subject_id = Database().create_subject_with_returned_id(
                name=subject_name,
                address=address,
                inn=inn,
                ogrn=ogrn,
                e_mail='',
                district='',

            )


            # внесение объекта, если это не рейд
            objects_adresses = result['addresses']
            objects_kinds = result['objectsKind']
            objects_risks = result['riskCategory']
            for address, kind, risk in zip(objects_adresses, objects_kinds, objects_risks):
                object_id = Database().create_object_with_returned_id(
                    subject=subject_id,
                    kind=kind,
                    address=address,
                    risk=risk,
                )
                Database().insert_m_to_m_object_inspection(
                    inspection_id=inspection_id,
                    object_id=object_id
                )
        else:
            # внесение субъекта, если это рейд
            risk = result['objectsKind'][0]
            kind = result['objectsKind'][0]
            for subject_name, inn, ogrn in zip(result['organizationsName'], result['organizationsInn'], result['organizationsOgrn']):
                subject_id = Database().create_subject_with_returned_id(
                    name=subject_name,
                    address="",
                    inn=inn,
                    ogrn=ogrn,
                    e_mail = '',
                    district='',
                )
                # внесение объекта, если это рейд
                object_id = Database().create_object_with_returned_id(
                    subject=subject_id,
                    kind=kind,
                    address="",
                    risk=risk,
                )

                Database().insert_m_to_m_object_inspection(
                    inspection_id=inspection_id,
                    object_id=object_id
                )


            # внесение объекта, если это рейд
            pass




    except Exception as ex:
        if special:
            logger.error(ex)
            logger.info(result)
            logger.warning('Проведена повторная попытка внесения с параметром special, результат неудачный.')
        return False


def new_insert_in_database(result: dict):

    try:
        Database().ultra_create_handler(result)

    except Exception as ex:

        logger.error(ex)
        logger.info(result)
        logger.warning('Проведена повторная попытка внесения с параметром special, результат неудачный.')
        return False


def create_tables_for_knms(knm):
    code = ''
    for key, value in knm.items():


        if isinstance(value, list):
            types = 'TEXT'
            code += f'{key} {types}, '
            continue

        elif value is None or isinstance(value, str):
            types = 'VARCHAR(255)'
            code += f'{key} {types}, '
            continue



        elif value is True or value is False:
            print('bool')
            types = 'BOOL'
            code += f'{key} {types}, '
            continue

        elif isinstance(value, int):

            types = 'INT'
            code += f'{key} {types}, '
            continue

    print(str(code).strip())


def insert_exceptions():
    with open('Exception_knm.json', 'r') as file:
        list_knm = json.load(file)

    database_inserts_conductor(list_knm)


def insert_from_json_with_multiple():
    with open('Plan_knm_full_2022.json', 'r') as file:
        list_knm = json.load(file)
    multiple_inserts(4, list_knm)


if __name__ == '__main__':
    # pass
    insert_exceptions()

