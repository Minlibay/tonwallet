import logging
from mnemonic import Mnemonic
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Настройка логирования
logging.basicConfig(
    filename='program.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

def generate_phrases():
    phrases = []
    for i in range(24):
        phrase = f"Сгенерированная фраза {i + 1}"
        phrases.append(phrase)
        logging.info(f"Сгенерирована фраза: {phrase}")
        print(f"Сгенерирована фраза: {phrase}")
    return phrases

def main():
    logging.info("Программа запущена")
    print("Программа запущена")

    phrases = generate_phrases()

    logging.info("Программа завершена")
    print("Программа завершена")

def generate_bip39_phrases(count=24, language='english'):
    mnemo = Mnemonic(language)
    phrase = mnemo.generate(strength=256)  # Генерация фразы из 24 слов
    return phrase.split()

def save_successful_phrase(phrase):
    with open("success.txt", "a") as f:
        f.write(f"{' '.join(phrase)}\n")
    logging.info(f"Фраза '{' '.join(phrase)}' сохранена в success.txt.")

def fill_phrases_in_browser(driver, phrases, attempt_number):
    wait = WebDriverWait(driver, 30)

    for i, word in enumerate(phrases):
        word_input = wait.until(EC.presence_of_element_located(
            (By.ID, f'import-mnemonic-{i}')))
        word_input.send_keys(word)
        time.sleep(0.5)
    logging.info(f"Попытка #{attempt_number}: Мнемоническая фраза введена.")

def process_wallet(attempt_number):
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')  # Запуск в headless-режиме (без графического интерфейса)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        while True:  # Бесконечный цикл для проверки фраз
            # Переходим на страницу MyTonWallet
            driver.get("https://mytonwallet.app/")
            logging.info(f"Попытка #{attempt_number}: Перешли на страницу MyTonWallet.")
            time.sleep(5)

            # Нажимаем на кнопку "24 секретных слова"
            wait = WebDriverWait(driver, 30)
            mnemonic_option = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), '24 секретных слова')]")))
            mnemonic_option.click()
            logging.info(f"Попытка #{attempt_number}: Выбрали опцию '24 секретных слова'.")
            time.sleep(3)

            # Генерация 24 слов
            phrases = generate_bip39_phrases()
            fill_phrases_in_browser(driver, phrases, attempt_number)

            # Нажимаем кнопку "Продолжить"
            continue_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Продолжить')]")))
            continue_button.click()
            logging.info(f"Попытка #{attempt_number}: Нажали кнопку 'Продолжить'.")

            time.sleep(5)

            # Проверка на сообщение об ошибке
            error_message = "Your mnemonic words are invalid"
            if error_message in driver.page_source:
                logging.warning(f"Попытка #{attempt_number}: Мнемоническая фраза неверная. Попытка снова.")
                driver.get("https://mytonwallet.app/")
                driver.delete_all_cookies()  # Очистка кеша и перезагрузка страницы
                time.sleep(5)
                continue

            # Если фраза правильная, сохраняем её
            save_successful_phrase(phrases)
            logging.info(f"Попытка #{attempt_number}: Фраза правильная, продолжаем.")

            # Выполняем дополнительные действия или перезагружаем страницу для нового цикла
            driver.get("https://mytonwallet.app/")
            driver.delete_all_cookies()
            time.sleep(5)
            break  # Завершаем цикл, если фраза правильная

    except Exception as e:
        logging.error(f"Попытка #{attempt_number}: Произошла ошибка: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    max_threads = 2  # Максимальное количество потоков
    attempt_counter = 0

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []

        for i in range(max_threads):
            attempt_counter += 1
            futures.append(executor.submit(process_wallet, attempt_counter))
            print(f"Запущено потоков: {len(futures)}")

        for future in as_completed(futures):
            print(f"Поток завершен с результатом: {future.result()}")

        print("Все потоки завершены.")