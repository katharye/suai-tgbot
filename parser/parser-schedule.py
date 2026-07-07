import aiohttp
import asyncio
from bs4 import BeautifulSoup

async def get_ids_group():
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
            
            start_tag  = soup.find('div', class_='lh-1').find('h4')
            print(start_tag.text)
            for sibling in start_tag.find_next_siblings():
                tag_name = sibling.text
                print(tag_name)




async def get_schedule_alls_groups():
    groups_ids = await get_ids_group()
    print(groups_ids)
    for key, id in groups_ids.items():
        await get_schedule_group(id)

async def main():
    await get_schedule_group(6698)

asyncio.run(main())