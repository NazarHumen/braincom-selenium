"""
Selenium parser for brain.com.ua: opens the main page, searches for
"Apple iPhone 15 128GB Black", opens the first search result and collects
the product fields, the photo links and the full characteristics dictionary,
prints the result and saves it to the Product table.
"""

from pprint import pprint
from random import uniform
from time import sleep

import undetected_chromedriver as uc
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from load_django import *
from parser_app.models import *

"""
uc.Chrome.__del__ calls quit() a second time when the object is garbage
collected; on Windows that second call fails with "The handle is invalid"
after the browser is already closed, so the repeated call is disabled.
"""
uc.Chrome.__del__ = lambda self: None

MAIN_URL = 'https://brain.com.ua/'
SEARCH_QUERY = 'Apple iPhone 15 128GB Black'
WAIT_TIMEOUT = 15


def pause(min_seconds=1.5, max_seconds=3.5):
    sleep(uniform(min_seconds, max_seconds))


def get_text(element):
    return ' '.join(element.get_attribute('textContent').split())


def launch_driver():
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument('--start-maximized')
    return uc.Chrome(options=chrome_options)


def get_url(driver, url):
    driver.get(url)
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[@class='header-bottom-in']"))
    )
    pause()


def search_product(driver, query):
    search_input = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable(
            (By.XPATH,
             "//div[@class='header-bottom-in']//input[@class='quick-search-input']")
        )
    )
    search_input.click()
    search_input.send_keys(query)

    search_button = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@class='qsr-submit']"))
    )
    search_button.click()

    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class, 'br-pcg-product-wrapper')]")
        )
    )
    pause()


def open_first_result(driver):
    first_result = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "(//div[contains(@class, 'br-pcg-product-wrapper')])[1]"
            "//div[contains(@class, 'br-pp-desc')]/a",
        ))
    )
    driver.execute_script('arguments[0].scrollIntoView({block: "center"});',
                          first_result)
    pause(0.5, 1.5)
    first_result.click()

    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, "//div[@class='br-pr-chr']"))
    )
    pause()


def get_product_data(driver):
    product = {}

    try:
        price_block = driver.find_element(
            By.XPATH, "//div[contains(@class, 'main-price-block')]"
        )
    except NoSuchElementException:
        price_block = None

    try:
        characteristics_block = driver.find_element(
            By.XPATH, "//div[@class='br-pr-chr']"
        )
    except NoSuchElementException:
        characteristics_block = None

    try:
        product['title'] = get_text(
            driver.find_element(By.XPATH, "//h1[@class='main-title']")
        )
    except NoSuchElementException:
        product['title'] = None

    try:
        product['color'] = get_text(characteristics_block.find_element(
            By.XPATH,
            ".//span[text()='Колір' or text()='Цвет']/following-sibling::span"
        ))
    except (NoSuchElementException, AttributeError):
        product['color'] = None

    try:
        product['memory'] = get_text(characteristics_block.find_element(
            By.XPATH,
            ".//span[text()=\"Вбудована пам'ять\" or text()='Встроенная память']"
            "/following-sibling::span"
        ))
    except (NoSuchElementException, AttributeError):
        product['memory'] = None

    try:
        product['manufacturer'] = get_text(characteristics_block.find_element(
            By.XPATH,
            ".//span[text()='Виробник' or text()='Производитель']"
            "/following-sibling::span"
        ))
    except (NoSuchElementException, AttributeError):
        product['manufacturer'] = None

    try:
        current_price = get_text(price_block.find_element(
            By.XPATH, ".//div[@class='br-pr-np']//span"
        ))
        try:
            product['price'] = get_text(price_block.find_element(
                By.XPATH, ".//div[@class='br-pr-op']//span"
            ))
            product['sale_price'] = current_price
        except NoSuchElementException:
            product['price'] = current_price
            product['sale_price'] = None
    except (NoSuchElementException, AttributeError):
        product['price'] = None
        product['sale_price'] = None

    try:
        product['images'] = [
                                image.get_attribute('src')
                                for image in driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'br-image-links')]"
                "//a[@class='product-modal-button']/img",
            )
                            ] or None
    except NoSuchElementException:
        product['images'] = None

    try:
        product['product_code'] = get_text(
            driver.find_element(By.XPATH, "//span[@class='br-pr-code-val']")
        )
    except NoSuchElementException:
        product['product_code'] = None

    try:
        product['reviews_count'] = int(get_text(driver.find_element(
            By.XPATH,
            "//a[contains(@class, 'scroll-to-element') "
            "and contains(@class, 'reviews-count')]/span",
        )))
    except (NoSuchElementException, ValueError):
        product['reviews_count'] = None

    try:
        product['screen_diagonal'] = get_text(
            characteristics_block.find_element(
                By.XPATH,
                ".//span[text()='Діагональ екрану' or text()='Диагональ экрана']"
                "/following-sibling::span"
            ))
    except (NoSuchElementException, AttributeError):
        product['screen_diagonal'] = None

    try:
        product['screen_resolution'] = get_text(
            characteristics_block.find_element(
                By.XPATH,
                ".//span[text()='Роздільна здатність екрану' "
                "or text()='Разрешение экрана']/following-sibling::span",
            ))
    except (NoSuchElementException, AttributeError):
        product['screen_resolution'] = None

    try:
        characteristics = {}
        for row in characteristics_block.find_elements(
                By.XPATH, ".//div[@class='br-pr-chr-item']/div/div"
        ):
            label, value = row.find_elements(By.XPATH, './span')
            characteristics[get_text(label)] = get_text(value)
        product['characteristics'] = characteristics or None
    except (NoSuchElementException, AttributeError, ValueError):
        product['characteristics'] = None

    product['search_query'] = SEARCH_QUERY
    product['link'] = driver.current_url

    return product


def save_product(product):
    Product.objects.get_or_create(**product)


def quit_driver(driver):
    driver.quit()


if __name__ == '__main__':
    driver = launch_driver()

    try:
        get_url(driver, MAIN_URL)
        search_product(driver, SEARCH_QUERY)
        open_first_result(driver)
        product = get_product_data(driver)
        pprint(product, sort_dicts=False)
        save_product(product)
    except TimeoutException as error:
        print(f'Page element did not load in time: {error.msg}')
    finally:
        quit_driver(driver)
