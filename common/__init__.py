import datetime

def timestamp(dt=None):
    dt = dt or datetime.datetime.now()
    dt_str = dt.isoformat(timespec='seconds')
    dt_str = dt_str.replace(':', '')
    dt_str = dt_str.replace('-', '')
    return dt_str
