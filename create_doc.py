from erknm.direct_pxl import Operation
import logging
from datetime import date
from pathlib import Path
import traceback


logging.basicConfig(format='%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s(%(lineno)d) - %(message)s',
                        filename=f'logging/{date.today().strftime("%d.%m.%Y")}.log', encoding='utf-8',
                        level=logging.INFO)
logger = logging.getLogger(Path(traceback.StackSummary.extract(traceback.walk_stack(None))[0].filename).name)


def str_from_list(some_list):
    string = ''
    for element in some_list:
        if string:
            string += f'; {element}'
        else:
            string += element
    return string



def make_xl_from_kmns(inspection):
    o = Operation()
    logger.info('Создаем файл')
    cell_pass = 2
    for n, knm in enumerate(kmns):
        controll_organ = inspection.terr_upr
        status = inspection.status


        addresses = str_from_list(knm['addresses'])
        startDate = inspection.date_start



        kind = inspection.kind
        erpId = inspection.number
        for name in knm['organizationsName']:

            name_index = knm['organizationsName'].index(name)
            organizationsName = knm['organizationsName'][name_index]
            organizationsOgrn = knm['organizationsOgrn'][name_index]
            organizationsInn = knm['organizationsInn'][name_index]
            cell_pass += name_index


            knm_columns = [
                controll_organ,
                status,
                organizationsName,
                organizationsOgrn,
                organizationsInn,
                addresses,
                startDate,
                kind,
                erpId
            ]

            for column in knm_columns:
                o.change_value_in_cell(
                    row=n+cell_pass,
                    column=knm_columns.index(column)+2,
                    value=column,
                    saving=False
                )
    logger.info('Файл наполнен данными, сохраняем')
    o.save_document(path="C:\\Users\\zaitsev_ad\\Documents\\ЕРКНМ\\Выгрузка общего плана 2023.xlsx")
    logger.info('Файл сохранен')


def main():
    pass


if __name__ == '__main__':
    main()

