from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

BASE_DIR = Path(__file__).parent.parent
ASSETS_DIR = BASE_DIR.parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
IMAGES_DIR = ASSETS_DIR / "images"

def generate_schedule_image(day_name: str, schedule_list: list[dict]) -> BytesIO:
    width = 850
    if not schedule_list:
        height = 220
    else:
        height = 130 + len(schedule_list) * 85
    
    # Создаём изображение с градиентным фоном (белый -> светло-голубой наискосок)
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    
    for y in range(height):
        for x in range(width):
            # Градиент наискосок: от белого (255, 255, 255) к светло-голубому (173, 216, 230)
            ratio = (x + y) / (width + height)
            r = int(255 + (173 - 255) * ratio)
            g = int(255 + (216 - 255) * ratio)
            b = int(255 + (230 - 255) * ratio)
            pixels[x, y] = (r, g, b)

    draw = ImageDraw.Draw(img)

    font_title = ImageFont.truetype(FONTS_DIR / "Comic Sans MS.ttf", 32)
    font_text = ImageFont.truetype(FONTS_DIR / "Comic Sans MS.ttf", 22)
    font_subtext = ImageFont.truetype(FONTS_DIR / "Comic Sans MS.ttf", 16)

    draw.text((30, 25), f"Расписание: {day_name.capitalize()}", font=font_title, fill=(30, 60, 90))
    draw.line((30, 75, width - 30, 75), fill=(100, 120, 140), width=2)

    y = 100
    if not schedule_list:
        draw.text((40, y), "Пар нет, можно отдыхать!", font=font_text, fill=(50, 70, 90))
    else:
        for item in schedule_list:
            lesson_type_display = f" [{item['lesson_type']}]" if item.get('lesson_type') else ""
            draw.text((40, y), f"{item['time']}  —  {item['subject']}{lesson_type_display}", font=font_text, fill=(30, 50, 70))
            
            sub_info = f"Ауд: {item['room']}   |   Преподователь: {item['teacher']}"
            draw.text((55, y + 32), sub_info, font=font_subtext, fill=(60, 80, 100))
            
            draw.line((40, y + 70, width - 40, y + 70), fill=(180, 200, 220), width=1)
            y += 85
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def generate_week_schedule_image(week_schedule: dict[str, list[dict]], week_text: str) -> BytesIO:
    """Генерирует картинку расписания на всю неделю."""
    width = 850
    
    # Вычисляем высоту в зависимости от количества пар
    total_lessons = sum(len(lessons) for lessons in week_schedule.values())
    if total_lessons == 0:
        height = 220
    else:
        height = 130 + total_lessons * 85 + len(week_schedule) * 40  # +40 для заголовков дней
    
    # Создаём изображение с градиентным фоном (белый -> светло-голубой наискосок)
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    
    for y in range(height):
        for x in range(width):
            # Градиент наискосок: от белого (255, 255, 255) к светло-голубому (173, 216, 230)
            ratio = (x + y) / (width + height)
            r = int(255 + (173 - 255) * ratio)
            g = int(255 + (216 - 255) * ratio)
            b = int(255 + (230 - 255) * ratio)
            pixels[x, y] = (r, g, b)

    draw = ImageDraw.Draw(img)

    font_title = ImageFont.truetype(FONTS_DIR / "Comic Sans MS.ttf", 32)
    font_day = ImageFont.truetype(FONTS_DIR / "Comic Sans MS.ttf", 26)
    font_text = ImageFont.truetype(FONTS_DIR / "Comic Sans MS.ttf", 20)
    font_subtext = ImageFont.truetype(FONTS_DIR / "Comic Sans MS.ttf", 14)

    draw.text((30, 25), f"Расписание: {week_text}", font=font_title, fill=(30, 60, 90))
    draw.line((30, 75, width - 30, 75), fill=(100, 120, 140), width=2)

    y = 100
    days_order = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    
    for day in days_order:
        if day not in week_schedule or not week_schedule[day]:
            continue
        
        # Заголовок дня
        draw.text((30, y), f"{day.capitalize()}", font=font_day, fill=(200, 100, 50))
        y += 35
        
        # Пары
        for item in week_schedule[day]:
            lesson_type_display = f" [{item['lesson_type']}]" if item.get('lesson_type') else ""
            draw.text((40, y), f"{item['time']}  —  {item['subject']}{lesson_type_display}", font=font_text, fill=(30, 50, 70))
            
            sub_info = f"Ауд: {item['room']}   |   Преподователь: {item['teacher']}"
            draw.text((55, y + 30), sub_info, font=font_subtext, fill=(60, 80, 100))
            
            draw.line((40, y + 65, width - 40, y + 65), fill=(180, 200, 220), width=1)
            y += 80
        
        y += 20  # Отступ между днями
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer