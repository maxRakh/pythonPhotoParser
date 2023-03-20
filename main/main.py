import os
import requests
from bs4 import BeautifulSoup
import lxml
from urllib.request import urlopen
from io import BytesIO
from PIL import Image
import datetime


def get_image_url(product_url: str, headers: dict) -> list:
    """Проходим по элементам словаря с названиями продуктов и ссылками на них получаем все ссылки на фотографии
    для каждой вещи и возвращаем список ссылок на фотографии для каждой вещи"""

    req_product = requests.get(url=product_url, headers=headers)
    soup = BeautifulSoup(req_product.text, "lxml")

    # Получаем id продукта для поиска соответствующего div
    rec_id_first_part = f"{product_url.split('/')[-1].split('-')[0]}"
    rec_id_sec_part = f"{product_url.split('/')[-1].split('-')[1]}"

    img_urls_soup = soup.find("div", {'id': f'{rec_id_first_part}'}).find("div", {
        'id': f't754__product-{rec_id_sec_part}'}).find('div', class_="t-slds__thumbsbullet-wrapper").find_all(
        'div', class_="t-slds__bgimg")

    img_urls_list = []
    for img_url_soup in img_urls_soup:
        img_urls_list.append(img_url_soup.get("data-original"))

    return img_urls_list


def get_data():
    """Получаем данные с bazzalagom.com.
    Скачиваем фотографии всех товаров, изменяем размер всех фото и формат,
    раскладываем по папкам /категория/товар/"""

    headers = {
        "accept": "*/*",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    }

    url = "https://bazzalagom.com/"
    req = requests.get(url=url, headers=headers)
    soup = BeautifulSoup(req.text, "lxml")

    # Собираем все названия разделов в список
    sections = soup.find_all("div", {'data-record-type': "473"})
    section_name_list = [section.find("h2").find("div").text for section in sections]

    # Собираем все группы товаров
    product_groups = soup.find_all('div', {'data-record-type': "754"})

    # Создаем словарь для словарей названий групп и списков на них ссылок на карточки всех продуктов
    product_urls_dict = {}

    # Наполняем список product_urls_list ссылками на все продукты
    for index, product_group in enumerate(product_groups):

        try:
            first_part_url = product_group.get("id")
        except:
            first_part_url = '****ERROR_FIRST_PART_URL*****'
        products_in_group = product_group.find_all("div", class_="t754__col t-col t-col_4 t-align_center "
                                                                 "t-item t754__col_mobile-grid js-product")
        # "Костыль". Создаем ключ словаря - группу товаров начиная с 5 минус -1, т.к. в телогрейках две группы товаров.
        if index < 4:
            product_urls_dict[section_name_list[index]] = {}
        if index > 4:
            product_urls_dict[section_name_list[index - 1]] = {}

        for product in products_in_group:
            try:
                second_part_url = product.get("data-product-lid")
            except:
                second_part_url = '****ERROR_SECOND_PART_URL*****'
            product_name = product.find("div", class_="t754__title t-name t-name_md js-product-name").get_text(separator=' ')
            product_url = f"https://bazzalagom.com/#!/tproduct/{first_part_url}-{second_part_url}"

            # Формируем словарь формата название категории: {название товара: url товара}
            if index < 4:
                product_urls_dict[section_name_list[index]][product_name] = product_url
            else:
                # "Костыль" нужный из-за того, что телогрейки идут двумя группами товаров
                product_urls_dict[section_name_list[index - 1]][product_name] = product_url

    # Создаем папку для сохранения данных по адресу "/Users/maxr/Downloads/" с названием по дате и времени создания
    time_now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    if not os.path.exists(f"/Users/maxr/Downloads/bazzalagom_img_{time_now}"):
        os.mkdir(f"/Users/maxr/Downloads/bazzalagom_img_{time_now}")
    os.chdir(f"/Users/maxr/Downloads/bazzalagom_img_{time_now}")

    print(f"Начинаем скачивать файлы в /Users/maxr/Downloads/bazzalagom_img_{time_now}")

    for category, items in product_urls_dict.items():
        len_url_list = len(items)

        for product_name, product_url in items.items():
            # Получим списки ссылок фотографий для каждого товава
            img_urls_list = get_image_url(product_url, headers)
            for index, img_url in enumerate(img_urls_list):
                # Создаем папку для каждой категории и для каждой веши, если они неще не созданы
                img_dir_path = make_dirs(product_name, category)
                # Изменяем размер и формат для каждой фотографии
                image = resize_img(img_url)
                # Сохраняем измененную фотографию
                save_image(image, index, img_dir_path)

            print(f"Скачаны фотографии {product_name}")


def resize_img(img_url: str):
    """Изменяем размер и расширение для каждой фотографии"""

    # Открываем изобразжение в виде байтовой строки, чтобы не скачивать перед изменением
    try:
        image = Image.open(BytesIO(urlopen(img_url).read()))
    except FileNotFoundError as ex:
        raise ex

    # Изменим ширину на 600, но сохраним пропорцию, предварительно ее посчитав.
    width, height = image.size
    aspect_ratio = width / height
    new_width = 600
    new_height = int(new_width / aspect_ratio)

    # Меняем размеры изображения
    image = image.resize((new_width, new_height), Image.LANCZOS)

    return image


def make_dirs(product_name: str, category: str) -> os.path:
    """Создаем папки для категории и для товара, предварительно проверив
    не существовали ли они уже до этого и возвращем путь до папки товара"""
    dir_name = f"{product_name}"
    if not os.path.exists(category):
        os.makedirs(os.path.join(category))
    if not os.path.exists(os.path.join(category, dir_name)):
        os.makedirs(os.path.join(category, dir_name))
    img_dir_path = os.path.join(category, dir_name)

    return img_dir_path


def save_image(image, index, img_dir_path):
    """Сохраняем измененные фотографии под названиями "порядковый номер.png"
    для каждой вещи в папку с названием веши"""
    image.save(os.path.join(img_dir_path, f"{index}.png"), "PNG")


if __name__ == '__main__':
    get_data()