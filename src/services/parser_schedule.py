import aiohttp
import asyncio
from bs4 import BeautifulSoup
from collections import defaultdict
import json 

async def get_ids_group() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get('https://guap.ru/rasp') as response:
            body = await response.text()

            soup = BeautifulSoup(body, 'html.parser')
            div = soup.find('div', class_='p-3 rounded d-print-none').find('select', id='selGroup').find_all('option')
            
            res = {}

            for i in div:
                res[i.get_text()] = i['value']
    res.pop('–нет–')
    return res


async def get_schedule_group(id):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://guap.ru/rasp_sm?gr={id}') as response:
            body = await response.text()

            soup = BeautifulSoup(body, 'html.parser')

            current_tag = soup.find('div', class_='lh-1').find('h4')

            cur_number_session = 0
            vne_setki = 0
            cur_item = ''
            res = defaultdict(dict)

            while current_tag:
                if current_tag.text == 'Вне сетки расписания':
                    cur_item = current_tag.text
                    res[cur_item] = []
                    vne_setki = 1
                elif current_tag.name == 'h4':
                    vne_setki = 0


                if current_tag.name == 'div' and str(current_tag.text)[0] in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                    cur_number_session = int(str(current_tag.text)[0])
                elif vne_setki == 1 and current_tag.text != 'Вне сетки расписания':
                    name, info = processing_outside_the_schedule_grid(current_tag)
                    res[cur_item].append({name: info})
                elif vne_setki == 0 and current_tag.name != 'h4' and current_tag.name != 'p':
                    name, info = get_session_info(current_tag, cur_number_session)
                    res[cur_item].append({name: info})
                    
                if current_tag.name == 'h4' and  current_tag.text != 'Вне сетки расписания':
                    cur_item = str(current_tag.text).lower()
                    res[cur_item] = []
                
                current_tag = current_tag.find_next_sibling()

            json_string = json.dumps(res, ensure_ascii=False, indent=4)
            print(json_string)

def processing_outside_the_schedule_grid(subject):
    data = subject.find_all('div')
    type_session = data[0].text.strip()
    direct_text = ''.join(
        t.strip() 
        for t in data[1].find_all(string=True, recursive=False) 
        if t.strip()
    )

    groups = data[1].find('a').text.strip()

    res = {
        'type_week': '-',
        'number_session': '-',
        'type_session': str(type_session).lower(),
        'audience': '-',
        'teacher': '-',
        'groups' : groups
    }

    return direct_text, res

def get_session_info(subject, cur_number_session):
    data = subject.find_all('div')

    type_session = data[0].text.strip()

    type_week = 'all'
    if (type_session[0] == '▲'):
        type_week = 'up'
        type_session = type_session[1:]

    elif (type_session[-1] == '▼'):
        type_week = 'down'
        type_session = type_session[:-1]

    direct_text = ''.join(
        t.strip() 
        for t in data[1].find_all(string=True, recursive=False) 
        if t.strip()
    )

    audience = (data[1].find('i').text)[2:]
    all_a = data[1].find_all('a')
    teacher = all_a[0].text

    groups = []

    for a in all_a[1:]:
        groups.append(a.text)

    res = {
        'type_week': type_week,
        'number_session': cur_number_session,
        'type_session': str(type_session).lower(),
        'audience': audience,
        'teacher': teacher,
        'groups' : ', '.join(groups)
    }

    return direct_text, res 
    

async def get_schedule_alls_groups():
    groups_ids = await get_ids_group()
    print(groups_ids)
    for key, id in groups_ids.items():
        await get_schedule_group(id)

# async def main():
#     await get_schedule_group(7382)

# asyncio.run(main())