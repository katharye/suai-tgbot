from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

BASE_DIR = Path(__file__).parent
FONTS_DIR = BASE_DIR / "fonts"
IMAGES_DIR = BASE_DIR / "images"

def generate_schedule_image(day_name: str, schedule_list: list[dict]) -> BytesIO:
    background_path = IMAGES_DIR / "background.png"
    img = Image.open(background_path)
    width = 850
    if not schedule_list:
        height = 220
    else:
        height = 130 + len(schedule_list) * 85
    try:
        img = Image.open(background_path).convert("RGB")
        img = img.resize((width, height))
        
    except OSError:
        img = Image.new("RGB", (width, height), color=(20, 30, 48))

    draw = ImageDraw.Draw(img)

    font_title = ImageFont.truetype(FONTS_DIR / "Comic Sans MS.ttf", 32)
    font_text = ImageFont.truetype(FONTS_DIR / "Comic Sans MS.ttf", 22)
    font_subtext = ImageFont.truetype(FONTS_DIR / "Comic Sans MS.ttf", 16)

    draw.text((30, 25), f"Расписание: {day_name.capitalize()}", font=font_title, fill=(135, 206, 250))
    draw.line((30, 75, width - 30, 75), fill=(200, 200, 200), width=2)

    y = 100
    if not schedule_list:
        draw.text((40, y), "Пар нет, можно отдыхать!", font=font_text, fill=(255, 255, 255))
    else:
        for item in schedule_list:
            draw.text((40, y), f"{item['time']}  —  {item['subject']}", font=font_text, fill=(255, 255, 255))
            
            sub_info = f"Ауд: {item['room']}   |   Преподователь: {item['teacher']}"
            draw.text((55, y + 32), sub_info, font=font_subtext, fill=(170, 200, 240))
            
            draw.line((40, y + 70, width - 40, y + 70), fill=(70, 90, 120), width=1)
            y += 85
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img.show(buffer)
#для теста

day_name = "понедельник"

schedule_list = [
    {
        "time": "09:30 - 11:00",  
        "subject": "Высшая математика",
        "room": "23-14",
        "teacher": "Иванов И.И."
    },
    {
        "time": "11:10 - 12:40",  
        "subject": "Физика (Лаб)",
        "room": "12-04",
        "teacher": "Петров П.П."
    },
    {
        "time": "13:00 - 14:30",  
        "subject": "Информатика",
        "room": "44-01",
        "teacher": "Сидоров С.С."
    }
]

#schedule_list = []

generate_schedule_image(day_name, schedule_list)