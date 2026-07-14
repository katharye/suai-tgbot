from datetime import datetime

def get_time_notifications_one_session(strr: str)->int | None: # в секундах
    # ЧЧ ММ
    # НАПИШИТЕ В ФОРМАТЕ ....
    # ЧЧ:ММ (пример: 01:20)
    
    try:
        t = strr.split(':')
        return int(t[0]) * 3600 + int(t[1]) * 60
    except Exception:
        return None

def get_time_notifications_all_session(strr: str)->int | None:
    try:
        res_time = datetime.strptime(strr, "%H:%M").time()
        return res_time
    except Exception:
        return False
