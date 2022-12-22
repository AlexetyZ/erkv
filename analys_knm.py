
import re
from pathlib import Path
from erknm.direct_pxl import Operation
from datetime import  date
import json
import logging
from erknm.main_ERKNM import erknm
from erknm.sql import Database
from erknm.exp import simple_analys_from_db, request_db

logging.basicConfig(format='%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s(%(lineno)d) - %(message)s',
                    filename=f'logging/reports/{date.today().strftime("%d.%m.%Y")}.log', encoding='utf-8',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class Analys:
    def __init__(self, path_xl_table: str or bool = None, path_json: str or bool = None):
        logger.info('Инициация класса Analys...')
        """

        :param path_xl_table: файл формата xlsx, содержащий анализируемы сведения.
                Должен содержать шапку в одну строчку, чтобы данные начиналисть со второй строки
                (НЕ Обязательный параметр, так как не все функции нуждаются в инициации экземпляря Operation для exel.)

        """

        if path_xl_table is not None:
            logger.info('Передан документ exel, привлекаем объект Operation')
            try:
                self.o = Operation(path_xl_table)
            except Exception as ex:
                logger.warning(ex)
                raise Exception(ex)

            logger.info('объект Operation для документа exel инициализирован')

        if path_json is not None:
            logger.info('Передан документ json, распаковываем в словарь')
            try:
                with open(path_json, 'r') as file:
                    self.analysed_dict = json.load(file)
            except Exception as ex:
                logger.warning(ex)
                raise Exception(ex)

            logger.info('Документ json, распакован в словарь')

    def knm_status_consists(self, external_dict: list or bool = None):
        """
        Принимает необязательный параметр
        """
        if self.analysed_dict is None:
            if external_dict is None:
                raise Exception('Стоп, так не пойдет! Либо передавай json файл в экземпляр класса, либо передавай '
                                'список прямо в эту функцию, анализировать нечего!')
            self.analysed_dict = external_dict


        objects_count = 0
        iskl = 0
        iskl_appealed = 0
        have_remark = 0
        wait_for_control = 0
        ready_to_apply = 0
        in_process = 0
        on_approval = 0
        else_status = []
        logger.info(f"файл прочитан, приступаем к анализу")
        for number, knm in enumerate(self.analysed_dict):
            addresses = knm['addresses']

            status = knm['status']
            if status == 'Исключена':
                iskl += 1
            elif status == 'Исключение обжаловано':
                iskl_appealed += 1
                wait_for_control += 1
                objects_count += len(addresses)
            elif status == "Ожидает проведения":
                wait_for_control += 1
                objects_count += len(addresses)
            elif status == "Есть замечания":
                have_remark += 1
                wait_for_control += 1
                objects_count += len(addresses)
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
        logger.info(f"Анализ завершен, вывожу результаты")

        logger.info(f"Всего объектов, подлежащих проверке в 2023 году {objects_count}")

        logger.info(f'Всего внесенных проверок на 2023 г - {len(self.analysed_dict)}')
        logger.info(f'проверок в строю, которые будут проводиться в 2023 г - {wait_for_control}')
        logger.info(f'исключено совсем проверок в 2023 г - {iskl}')
        logger.info(
            f'обжалованные проверок, кроме исключенных совсем в 2023 г (входят в те, что будут проводиться) - {iskl_appealed}')
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

    def moda_in_list_for_even(self, column: str = 'A', start_from_row: int = 2,
                              notation_power_set: str = 'Количество территорий, где есть нарушения') -> dict:
        """
        1. Анализ таблицы exel с выявленными нарушениями по заданному столбцу (например список кнм с нарушениями,
                где нужно исследовать столбец с ТУ, допустившими нарушение)
        2. Ведет отчет по количеству и составу объектов согласно таблице, с выявлением мощности множества
                и составления рейтинга встречаемости, вынося все в отдельную табличку вместе с основной таблицей

        :param start_from_row: с какой строки таблицы начинаем анализировать текст, по умолчанию - 2
        :param column: колонка в которой содержатся анализируемые данные, по умолчанию - А
        :param notation_power_set: обозначение мощности множества,
                количество уникальных значений в исследуемом множестве,
                например, частота встречаемости ТО в списке нарушителей.

        :return: словарь, состоящий из количества элементов - мощности множества
                и фразы, отражающей частоту встечаемости конкретного элемента в множестве
        """
        if self.o is None:
            logger.error('Не передан критический для функции moda_in_list_for_even документ exel')
            raise Exception(
                'Эй! Так не пойдет. Эта функция анализирует только таблицу exel,'
                ' так что будь добр, передай в класс этой функции путь к файлу в path_xl_table, '
                'а сейчас:  path_xl_table is None')

        terr_upr_list = []
        values = self.o.get_list_from_sh_column(column, start_from_row=start_from_row)
        for value in values:
            terr_upr_list.append(value[0])

        unic_terr_upr_list = set(terr_upr_list)
        power_set = f'{notation_power_set} - {len(unic_terr_upr_list)}'
        phrase = ''
        moda_for_even_terr_upr = []

        for terr_upr in unic_terr_upr_list:
            moda_for_even_terr_upr.append({'name': terr_upr, 'count': terr_upr_list.count(terr_upr)})

        moda_for_even_terr_upr = sorted(moda_for_even_terr_upr, key=lambda d: d['count'], reverse=True)

        filepath = self.o.create_doc_in_this_path('рейтинг нарушений')
        logger.info(f'создан документ "рейтинг нарушений" в расположении')
        o_1 = Operation(filepath)
        o_1.change_value_in_cell(row=1, column=1, value='Территориальное управление', saving=False)
        o_1.change_value_in_cell(row=1, column=2, value='Количество паспортов с выявленными нарушениями', saving=False)
        for number, element in enumerate(moda_for_even_terr_upr):
            o_1.change_value_in_cell(row=number + start_from_row, column=1, value=element['name'], saving=False)
            o_1.change_value_in_cell(row=number + start_from_row, column=2, value=element['count'], saving=False)
            phrase += f"{element['name']} ({element['count']}), "
        o_1.save_document()
        logger.info(f'создан документ "рейтинг нарушений" в расположении {Path(o_1.return_path_file())}')
        logger.info({power_set: phrase})
        return {power_set: phrase}


    def get_knm_without_stop_date(self):
        text_request = request_db(
            targets=['id'],
            year=2022,
            status=[
                'Завершено',
                # 'Решение обжаловано',
                # 'В процессе заполнения',
                # 'Ожидает завершения',
                # 'Не может быть проведено',
                # 'Не согласована',
                # 'Исключена'
            ],
            start_date=['2022-01-01', '2022-09-30'],
            stop_date='1900-01-01',
            controll_organ=[
                'Управление Роспотребнадзора по Республике Бурятия',
                'Управление Роспотребнадзора по Республике Саха (Якутия)',
                'Управление Роспотребнадзора по Забайкальскому краю',
                'Управление Роспотребнадзора по Камчатскому краю',
                'Управление Роспотребнадзора по Приморскому краю',
                'Управление Роспотребнадзора по Хабаровскому краю',
                'Управление Роспотребнадзора по Амурскоу области',
                'Управление Роспотребнадзора по Магаданской области',
                'Управление Роспотребнадзора по Сахалинской области',
                'Управление Роспотребнадзора по о Еврейской автономной области',
                'Управление Роспотребнадзора по Чукотскому автономному округу'
            ]
        )

        result = Database().take_request_from_database(text_request)
        print(len(result))
        s = erknm(headless=True)
        s.autorize()
        for n, erknm_id in enumerate(result):
            erpId = erknm_id[0]
            full_knm_info = s.get_knm_by_number(erpId)
            print(n)
            try:
                true_stop_date = full_knm_info['knmErknm']['organizations'][0]['act']['nextWordDayActDateTime']

            except:
                true_stop_date = re.search(r"\d{4}-\d{2}-\d{2}", full_knm_info['statusDateCreate']).group()

            Database().change_stop_date_by_erpID(true_stop_date, erpId)



    def get_consists(self):
        simple_analys_from_db(
            targets=['id'],
            year=2022,
            status=[
                'Завершено',
                'Решение обжаловано',
                'В процессе заполнения',
                'Ожидает завершения',
                # 'Не может быть проведено',
                # 'Не согласована',
                # 'Исключена'
            ],
            start_date=['2022-01-01', '2022-03-31'],
            stop_date='1900-01-01',
            controll_organ=[
                'Управление Роспотребнадзора по Республике Бурятия',
                'Управление Роспотребнадзора по Республике Саха (Якутия)',
                'Управление Роспотребнадзора по Забайкальскому краю',
                'Управление Роспотребнадзора по Камчатскому краю',
                'Управление Роспотребнадзора по Приморскому краю',
                'Управление Роспотребнадзора по Хабаровскому краю',
                'Управление Роспотребнадзора по Амурскоу области',
                'Управление Роспотребнадзора по Магаданской области',
                'Управление Роспотребнадзора по Сахалинской области',
                'Управление Роспотребнадзора по о Еврейской автономной области',
                'Управление Роспотребнадзора по Чукотскому автономному округу'
            ]

        )


if __name__ == '__main__':

    a = Analys()
    a.get_knm_without_stop_date()
#     # path = Path("S:\Зайцев_АД\письма в территории\О недопущении нарушений в ЕРКНМ\d_120500527.xlsx")
#     print(datetime.now().strftime('%d.%m.%Y'))
