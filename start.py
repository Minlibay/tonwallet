import logging
from mnemonic import Mnemonic
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
import concurrent.futures

# Настройка логирования
logging.basicConfig(
    filename='program.log',  # Название файла лога
    level=logging.INFO,  # Уровень логирования
    format='%(asctime)s - %(levelname)s - %(message)s',  # Формат сообщений в логе
)

PROGRESS_FILE = "progress.json"

def generate_bip39_phrases(count=1, language='english'):
    mnemo = Mnemonic(language)
    phrases = []
    for _ in range(count):
        phrase = mnemo.generate(strength=128)
        phrases.append(phrase)
    return phrases

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            logging.info("Загрузка прогресса из файла.")
            return json.load(f)
    return {}

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)
    logging.info("Прогресс сохранен.")

def fill_phrases_in_browser(phrases, progress):
    options = webdriver.ChromeOptions()
    options.debugger_address = "127.0.0.1:9222"  # Подключение к открытому браузеру

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    password = "YourSecurePassword123!"  # Здесь задайте ваш пароль

    try:
        while True:  # Бесконечный цикл до тех пор, пока не будет найден нужный баланс
            phrase = generate_bip39_phrases()[0]
            if phrase in progress:
                logging.info(f"Фраза '{phrase}' уже обработана, пропуск.")
                continue

            wait = WebDriverWait(driver, 40)

            # Проверяем, если появилось окно подтверждения пароля
            if "Подтвердите пароль" in driver.page_source:
                password_input = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//input[@data-testid='password-field']")))

                # Вводим пароль
                password_input.send_keys(password)
                logging.info("Пароль введен.")

                # Добавляем паузу, чтобы кнопка могла стать активной
                time.sleep(2)

                # Выполняем JavaScript, чтобы нажать клавишу "ENTER"
                driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {'key': 'Enter'}));",
                                      password_input)

                logging.info("Клавиша 'ENTER' нажата через JavaScript.")
                continue  # Перезапускаем цикл

            # Проверяем, если появилось окно для ввода 12 слов
            if "Импортировать, используя секретную фразу" in driver.page_source:
                logging.info("Обнаружен экран для ввода 12 слов мнемонической фразы.")
                for i, word in enumerate(phrase.split(), start=1):
                    word_input = wait.until(EC.presence_of_element_located(
                        (By.XPATH, f"//input[@placeholder='Word #{i}']")))
                    word_input.send_keys(word)
                    time.sleep(0.5)
                logging.info("Мнемоническая фраза введена.")

            # Переходим на страницу восстановления кошелька
            driver.get("chrome-extension://egjidjbpglichdcondbcbdnbeeppgdph/home.html#/onboarding/")
            time.sleep(3)
            logging.info("Перешли на страницу восстановления кошелька.")

            # Нажимаем кнопку "Импортировать или восстановить кошелек"
            import_text = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//p[contains(text(), 'Импортировать или восстановить кошелек')]")))
            import_button = import_text.find_element(By.XPATH, "./..")
            import_button.click()
            logging.info("Нажата кнопка 'Импортировать или восстановить кошелек'.")

            time.sleep(3)

            # Вводим новый пароль
            password_input = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@data-testid='password-field']")))
            password_input.send_keys(password)
            logging.info("Введен пароль.")

            # Вводим подтверждение пароля
            confirm_password_input = wait.until(
                EC.presence_of_element_located((By.XPATH, "(//input[@data-testid='password-field'])[2]")))
            confirm_password_input.send_keys(password)
            logging.info("Пароль подтвержден повторно.")

            # Ставим галочку на согласие с условиями обслуживания
            agreement_checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox']")))
            agreement_checkbox.click()
            logging.info("Галочка на согласие с условиями обслуживания установлена.")

            # Нажимаем кнопку "Далее"
            final_next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Далее')]")))
            final_next_button.click()
            logging.info("Нажата кнопка 'Далее'.")

            time.sleep(3)

            # Заполнение полей для ввода мнемонической фразы
            for i, word in enumerate(phrase.split(), start=1):
                word_input = wait.until(EC.presence_of_element_located(
                    (By.XPATH, f"//input[@placeholder='Word #{i}']")))
                word_input.send_keys(word)
                time.sleep(0.5)
            logging.info("Мнемоническая фраза введена.")

            # Нажимаем кнопку "Далее" на странице с мнемонической фразой
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Далее')]")))
            next_button.click()
            logging.info("Нажата кнопка 'Далее' после ввода фразы.")

            time.sleep(3)

            # Нажимаем кнопку "Нет, спасибо"
            no_thanks_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//p[contains(text(), 'Нет, спасибо')]//ancestor::button")))
            no_thanks_button.click()
            logging.info("Нажата кнопка 'Нет, спасибо'.")

            time.sleep(3)

            # Нажимаем кнопку "Открыть кошелек"
            open_wallet_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Открыть кошелек')]")))
            open_wallet_button.click()
            logging.info("Нажата кнопка 'Открыть кошелек'.")

            time.sleep(4)

            # Закрываем подсказку, нажав на крестик
            close_tip_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@data-testid='close-modal-button']")))
            close_tip_button.click()
            logging.info("Подсказка закрыта.")

            time.sleep(15)

            # Проверяем баланс
            balance_text = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//h2[contains(@class, 'massive-text')]")))
            balance = float(balance_text.text.replace('$', '').replace('\u00A0', '').replace(',', '.'))

            progress[phrase] = balance
            save_progress(progress)

            # Выводим баланс в консоль
            print(f"Баланс: {balance}")

            if balance > 0:
                with open("success.txt", "a") as f:
                    f.write(f"Phrase: {phrase}, Password: {password}, Balance: ${balance}\n")
                logging.info(f"Фраза {phrase} с балансом ${balance} сохранена в success.txt.")

            logging.info(f"Баланс: {balance}")

            if balance >= 1000:
                logging.info("Найден кошелек с балансом более 1000$. Завершение работы.")
                return  # Завершаем работу программы, если найден нужный баланс

            # Нажатие на "Mnemonic 1"
            mnemonic_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//p[@data-testid='selected-wallet-name']")))
            mnemonic_button.click()
            logging.info("Нажатие на 'Mnemonic 1'.")

            time.sleep(3)

            # Нажатие на "Управление кошельками"
            manage_wallets_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@data-testid='wallet-select-popup-manage-wallets-button']")))
            manage_wallets_button.click()
            logging.info("Нажатие на 'Управление кошельками'.")

            time.sleep(3)

            # Нажатие на 3 точки для управления кошельком
            more_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@data-testid='popover-show-action']")))
            more_button.click()
            logging.info("Нажатие на 3 точки для управления кошельком.")

            time.sleep(3)

            # Нажатие на "Удалить кошелек"
            delete_wallet_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@data-testid='popover-action-delete']")))
            delete_wallet_button.click()
            logging.info("Нажатие на 'Удалить кошелек'.")

            time.sleep(3)

            # Нажимаем кнопку "OK, продолжить"
            ok_continue_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'ОК, продолжить')]")))
            ok_continue_button.click()
            logging.info("Нажатие на 'OK, продолжить'.")



    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    language = 'english'

    progress = load_progress()

    while True:  # Бесконечный цикл генерации и проверки фраз
        bip39_phrases = generate_bip39_phrases(1, language)
        fill_phrases_in_browser(bip39_phrases, progress)