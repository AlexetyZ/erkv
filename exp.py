import decimal
import json
import re
import time
from datetime import  date, timedelta
import logging
from Bot_telegram import send_message_to_terr_upr
from erknm.sql import Database
from pathlib import Path
import traceback
from erknm.direct_pxl import Operation
from multiprocessing import Pool
from itertools import groupby
from erknm.main_ERKNM import erknm
# from direct_sql import database_inserts_conductor

logging.basicConfig(format='%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s(%(lineno)d) - %(message)s',
                        filename=f'logging/{date.today().strftime("%d.%m.%Y")}.log', encoding='utf-8',
                        level=logging.INFO)
logger = logging.getLogger(Path(traceback.StackSummary.extract(traceback.walk_stack(None))[0].filename).name)

d = Database()
exception_knm = []

def report():


    logger.info(f"старт программы, читаем файл")
    with open("Plan_knm_full_2023.json", 'r') as file:
        list = json.load(file)
    iskl = 0
    iskl_appealed = 0
    have_remark = 0
    wait_for_control = 0
    ready_to_apply = 0
    in_process = 0
    on_approval = 0
    else_status = []
    logger.info(f"файл прочитан, приступаем к анализу")
    for number, knm in enumerate(list):

        status = knm['status']
        if status == 'Исключена':
            iskl += 1
        elif status == 'Исключение обжаловано':
            iskl_appealed += 1
            wait_for_control += 1
        elif status == "Ожидает проведения":
            wait_for_control += 1
        elif status == "Есть замечания":
            have_remark += 1
            wait_for_control += 1
        elif status == 'Готово к согласованию':
            ready_to_apply += 1
        elif status == 'В процессе заполнения':
            else_status.append(knm)
            in_process += 1
        elif status == 'На согласовании':
            on_approval += 1
            else_status.append(knm)

        else:
            else_status.append(knm)
    logger.info(f"Анализ завершен, вывожу результаты...")

    logger.info(f'Всего внесенных проверок на 2023 г - {len(list)}')
    logger.info(f'проверок в строю, которые будут проводиться в 2023 г - {wait_for_control}')
    logger.info(f'исключено совсем проверок в 2023 г - {iskl}')
    logger.info(f'обжалованные проверок, кроме исключенных совсем в 2023 г (входят в те, что будут проводиться) - {iskl_appealed}')
    logger.info(f'количество проверок в 2023 г, имеющие замечания - (входят в те, что будут проводиться) - {have_remark}')
    logger.info(f'количество проверок в 2023 г, имеющие статус "Готово к согласованию" - {ready_to_apply}')
    logger.info(f'количество проверок в 2023 г, "В процессе заполнения" - {in_process}')
    logger.info(f'количество проверок в 2023 г, "На согласовании" - {on_approval}')


    len_else_status = len(else_status)
    logger.info(f'Имеющие другой статус: {len_else_status}')

    if len_else_status != 0:
        for number, else_knm in enumerate(else_status):
            logger.info(number)
            logger.info(else_knm)
            logger.info('')


def formatter(text: str):
    text = text.replace('"', '')
    return text


def main():

    with open('Exception_knm.json', 'r') as file:
        list_knm = json.load(file)


    multiple_inserts(list_knm)


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

        result = insert_in_database(knm)
        if result is False:
            try:
                result = insert_in_database(knm, special=True)
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

    result = insert_in_database(knm)
    if result is False:
        try:
            result = insert_in_database(knm, special=True)
            if result is False:
                logger.info('Возникла ошибка, с которой не удалось справиться...')
                exception_knm.append(knm)
        except Exception as ex:
            logger.info(f'Непредвиденная ошибка строка 90: {ex}')
            exception_knm.append(knm)


def multiple_inserts(processes: int, knm_list: list):
    logger.info('старт программы')
    pool = Pool(processes)
    pool.map(database_inserts_conductor_for_multiprocessing, knm_list)
    if len(exception_knm) > 0:
        with open('Exception_knm.json', 'w') as file:
            json.dump(exception_knm, file)
            result = f'По итогу внесения не было внесено {len(exception_knm)} проверок. Они упакованы в файл Exception_knm.json и их ошибки ожидают решений'
            logger.info(result)
        return result
    logger.info('Все проверки успешно занесены!')


def insert_in_database(knm: dict, special: bool = False) -> bool:
    """
    Функция непосредственного внесения в базу данных
    @param knm: словарь сведений о кнм, как правило в формате json (список json-ов) для загрузки в базу данных
    @param special: параметр, включаемый для повторного включения, является более медленным, так как при значении  True
        заменяет значения в адресах субъектов
    @return: значение True или False при успешном выполнении инсёрта, и соответственно, ошибке при выполнении инсёрта

    """
    data = str(knm).replace('"', '').replace('None', "'None'").replace('False', "'False'")\
        .replace('True', "'True'").replace("'", '"').replace('\n', '').replace('\\n', '').replace('\\r', '').replace('\\t', '').replace('\\p', '').replace("\\", "/")
    try:
        id = int(knm['erpId'])
        true_id = int(knm['id'])
        kind = knm['kind']
        try:
            type = knm['knmType']
        except:
            type = knm['type']['name']
        status = knm['status']
        year = int(knm['year'])
        start_date = knm['startDateEn']
        stop_date = knm['stopDateEn']
        if stop_date is None:
            stop_date = '1900-01-01'
        inn = knm['inn']
        ogrn = knm['ogrn']
        try:
            risk = knm['riskCategory'][0]
        except:
            risk = 'NULL'

        try:
            object_kind = knm['objectsKind'][0]
        except:
            object_kind = 'NULL'
        controll_organ = knm['controllingOrganization']
        if special is True:
            addresses = []
            for address in knm['addresses']:
                address = str(address).replace("'", "").replace('"', '').replace("''", "")
                addresses.append(str(address))
            knm['addresses'] = addresses
        Database().create_json_formate_knm_in_raw_knm(id, kind, type, status, year, start_date, stop_date, inn, ogrn, risk, object_kind, controll_organ, data)
        return True

    except Exception as ex:
        logger.error(ex)
        logger.info(data)
        logger.info(knm)
        logger.info('')
        return False


def request_db(targets: list, table: str = 'erknm', **params):
    target_text = ''
    for target in targets:
        if target_text:
            target_text += f', {target}'
        else:
            target_text += target
    params_text = ''
    for db_column, value in params.items():
        # print(value[0])
        if isinstance(value, list):
            if re.search(r'\d{4}-\d{2}-\d{2}', str(value[0])) and re.search(r'\d{4}-\d{2}-\d{2}', str(value[1])):
                if params_text:
                    params_text += f" AND ({db_column} BETWEEN '{value[0]}' AND '{value[1]}')"
                else:
                    params_text += f" WHERE ({db_column} BETWEEN '{value[0]}' AND '{value[1]}')"

            else:
                values_text = ''
                for v in value:
                    if values_text:
                        values_text += f", '{v}'"
                    else:
                        values_text += f"'{v}'"
                if params_text:
                    params_text += f" AND {db_column} IN ({values_text})"
                else:
                    params_text += f" WHERE {db_column} IN ({values_text})"
        else:
            if params_text:
                params_text += f" AND {db_column}='{value}'"
            else:
                params_text += f" WHERE {db_column}='{value}'"
    if params_text:
        text = f"""SELECT {target_text} FROM {table}{params_text};"""
    else:
        text = f"""SELECT {target_text} FROM {table};"""
    return text


def create_xl_with_result(responce):
    o = Operation()
    for row_number, row in enumerate(responce):
        for column_number, value in enumerate(row):
            if isinstance(value, decimal.Decimal):
                value = f"{decimal.Decimal(value)}"


            o.change_value_in_cell(row_number+2, column_number+2, value)

    o.save_document(path='Отчет по нарушению сроков')


def group(set_1):
    """
    принимает множество подмножеств из 2 состовляющих, например (('val1', 'val2'), ('val1', 'val4'), ('val5', 'val6'))
        и группирует их по первому значению подмножества.
    @param set_1: то самое множество
    @return: dict из отсортированных вторых значений подмножеств по первым значениям подмножеств, из примера выше:
        {'val1': ['val2', 'val4'], 'val5': ['val6']}
    """
    set_2 = {}
    for v in groupby(set_1, key=lambda x: x[0]):
        set_2[v[0]] = [i[1] for i in v[1]]
    return set_2


def send_about_voilation_status(responce, message_theme: str = 'Внимание! \n срочно исправить статус паспорта/ов КНМ:\n'):
    """

    @param responce: сырой ответ из базы данных в оношении определенного вида нарушений, состоящий из парных значений, где первое значение
        - наименование органа контроля, ответственного за заполнение паспорта КНМ,
        а второе - номер паспорта КНМ, в котором неиобходимо исправитьошибки, указанные в теме
    @param message_theme: тема сообщения, где важно указать, что именно нужно исправить ответственным в паспортах КНМ
    @return: ничего не ретерн, просто отправляет сообщения через бота или принтует, когда отладка
    """
    send_message_to_terr_upr(message_theme)
    # print(message_theme)

    for key, value in group(responce).items():
        message = ''
        message += f'{key}:\n'
        for v in value:
            message += f'{v}\n'
        send_message_to_terr_upr(message)
        time.sleep(11)
        print(message)

def find_violations():
    chek_old_violations()
    status_violations()   # потом раскомментить обязательно

def chek_old_violations(reason: str = 'status'):
    delete_with_right_status()   # потом раскомментить обязательно
    viol_erknm_id_list = d.take_request_from_database(f"""SELECT erknm_id, id FROM viol where verify=0;""")
    s = erknm(headless=True)
    s.autorize()


    knm_detail_list = []
    len_id_list = len(viol_erknm_id_list)
    for n, erknm_id in enumerate(viol_erknm_id_list):
        print(f'{n+1}/{len_id_list}')
        try:
            responce = s.get_knm_by_number(erknm_id[0])
            knm_detail_list.append(responce)
            d.change_verify_where_knm_already_checked(f'{erknm_id[0]}{reason}')
        except IndexError:
            d.delete_all_info_about_knm_by_erp_id(erknm_id[0])


    database_inserts_conductor(knm_detail_list)



def delete_with_right_status():
    d.take_request_from_database(f"""DELETE FROM viol WHERE id IN (SELECT concat(id, 'status') from erknm where id in (SELECT erknm_id from (select * from viol) as t2) and status in ('Завершено', 'Удалено'));""")
    d.commit()

def status_violations():
    """
    Функция выявления ошибок статуса, берет начало года и дату 25 дней назад и в этом диапозоне ищет проверки
        со статусами "Ожидает завершения", "В процессе заполнения", "Ожидает проведения"
        (а они должны иметь на эту дату другой статус - следственно, нарушение)
        формирует данные в отдельную таблицу viol
        найденные паспорта КНМ передает в чат-бота для отправки адресатам
    @return:
    """
    actual_year = date.today().year
    date_start = f'{actual_year}-01-01'
    date_end = date.today()-timedelta(days=25)


    d.take_request_from_database(f"""INSERT INTO viol(id, erknm_id, reason, organ, rating) select CONCAT(id, 'status'), id, 'status',
    controll_organ, 1 FROM erknm WHERE status IN (
    "Ожидает завершения", "В процессе заполнения", "Ожидает проведения") AND (start_date BETWEEN '{date_start}' AND '{date_end}') ON DUPLICATE KEY UPDATE rating=rating+1;""")
    d.commit()
    first_mistake = d.take_request_from_database(f"""SELECT organ, erknm_id FROM viol WHERE reason='status' AND rating=1;""")
    if len(first_mistake) > 1:
        send_about_voilation_status(first_mistake)

    second_and_more_mistake = d.take_request_from_database(f"""SELECT organ, erknm_id FROM viol WHERE reason='status' AND rating>1;""")
    if len(second_and_more_mistake) > 1:
        abusive_theme = 'Нижеуказанные паспорта КНМ не исправлены с момента последнего напоминания.\n Их учет тщательно ведется.\n Напоминаем, необходимо НЕМЕДЛЕННО исправить следующие паспорта:'
        send_about_voilation_status(second_and_more_mistake, message_theme=abusive_theme)


def get_data_knm_in_json(knm_number):
    responce = d.take_request_from_database(f"""SELECT data FROM erknm WHERE id='{knm_number}';""")
    data = json.loads(responce[0][0])
    return data


def binary_analys_from_db() -> dict:
    text_request = """SELECT risk FROM erknm WHERE year='2023' AND status IN ('Исключение обжаловано', 'Есть замечания', 'Ожидает проведения');"""
    request = d.take_request_from_database(text_request)


def get_cells_for_request_db(targets: list, table: str = 'erknm', **params):
    text_request = request_db(targets, table, **params)

    print(text_request)
    request = d.take_request_from_database(text_request)
    # for row in request:
    #     print(row)
    return request


def simple_analys_from_db(targets: list, table: str = 'erknm', **params) -> dict:
    """
    Функция выполнения простого анализа одинарного селекта по представленным параметрам

    @param targets: предмет анализа - что нужно разложить по категориям, то есть что является исследуемой выборкой
    @param table: таблица из которой берется выборка
    @param params: параметры, по которым отбирается выборка из таблицы базы данных
    @return:
        Возвращает результат анализа, дублирует в принт для красивого представления и в лог для кеширования результата
    """
    text_request = request_db(targets, table, **params)

    request = d.take_request_from_database(text_request)
    result = {}
    responce = []
    if len(request) > 0:
        for req in request:
            responce.append(req[0])
        result['количество результатов'] = len(responce)
        result['мощность выборки'] = len(set(responce))
        details = {}
        for kind in set(responce):
            details[kind] = responce.count(kind)
        result['details'] = dict(sorted(details.items(), key=lambda item: item[1], reverse=True))
        logger.info(f'{text_request}, {result}')

        for key, values in result.items():
            if key == 'details':
                for obj, value in values.items():
                    print(f'    {obj}: {value}')
            else:
                print(f'{key}: {values}')
        return result

def where_is_error_in_string_by_index(index: int, text: str):
    print(text)


if __name__ == '__main__':

    # result = get_cells_for_request_db(
    #     ['controll_organ', 'id'],
    #     year=2022,
    #     status=[
    #         "Ожидает завершения",
    #         "В процессе заполнения",
    #         "Ожидает проведения"
    #     ],
    #     start_date=['2022-11-01', '2022-11-17']
    # )
    #
    # send_about_voilation_status(result)
    find_violations()


