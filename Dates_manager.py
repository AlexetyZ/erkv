import calendar
import datetime
import math


def period_between_month(year: int = 2023, month: int = 1):
    month_last_day = calendar.monthrange(year, month)[1]
    start = datetime.date(year, month, 1).strftime('%Y-%m-%d')
    end = datetime.date(year, month, month_last_day).strftime('%Y-%m-%d')
    result = ({'start': str(start), 'end': str(end)})
    return result


def periods_into_month(year: int = 2023, month: int = 1, parts: int = 2):
    month_last_day = calendar.monthrange(year, month)[1]
    start = datetime.date(year, month, 1).strftime('%Y-%m-%d')
    part_month = math.floor(month_last_day/parts)
    # print(part_month)
    result = []
    day = 1
    for part in range(parts):
        start_part = datetime.date(year, month, day).strftime('%Y-%m-%d')
        if part == range(parts)[-1]:
            result.append({'start': start_part, 'end': datetime.date(year, month, month_last_day).strftime('%Y-%m-%d')})
        else:
            end_part = datetime.date(year, month, day+part_month).strftime('%Y-%m-%d')
            result.append({'start': start_part, 'end': end_part})

            day = day+part_month
            day += 1

    return result


def split_period(date_start, date_end, parts: int = 2):
    start = datetime.datetime.strptime(date_start, '%Y-%m-%d')
    end = datetime.datetime.strptime(date_end, '%Y-%m-%d')
    delta = (end - start).days + 1 - parts

    len_part = math.floor(delta/parts)
    print(len_part)


    result = []

    for part in range(parts):

        if part == range(parts)[-1]:
            result.append({'start': start.strftime('%Y-%m-%d'), 'end': end.strftime('%Y-%m-%d')})
        else:
            end_part = start + datetime.timedelta(days=len_part)
            result.append({'start': start.strftime('%Y-%m-%d'), 'end': end_part.strftime('%Y-%m-%d')})
            start += datetime.timedelta(days=len_part+1)

    return result


def split_year_for_periods(year: int, parts: int = 50):
    return split_period(date_start=f'{year}-01-01', date_end=f'{year}-12-31', parts=parts)


if __name__ == '__main__':
    dates = split_period(date_start='2022-01-01', date_end='2022-12-31', parts=52)
    print(dates)
