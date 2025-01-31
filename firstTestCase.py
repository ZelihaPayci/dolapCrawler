import pickle
import time
import re
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, Application, filters
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

def create_sent_products_table():
    conn = sqlite3.connect("sent_products.db")
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sent_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Unique ID for tracking
        search_id INTEGER, 
        url TEXT UNIQUE,                       -- Product URL (must be unique)
        title TEXT,                            -- Product title
        size TEXT,                             -- Product size
        condition TEXT,                        -- Product condition
        price REAL,                            -- Product price (stored as float)
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP -- Timestamp when it was added
    )
    ''')

    conn.commit()
    conn.close()

def create_search_criteria_table():
    try:
        conn = sqlite3.connect("search_criteria.db")
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_criteria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_term TEXT,
            desired_size TEXT,
            desired_price REAL,
            desired_condition TEXT,
            chat_id TEXT
        )
        ''')

        conn.commit()
        conn.close()
        print("search_criteria table created successfully.")
    except Exception as e:
        print(f"Error creating search_criteria table: {e}")


create_search_criteria_table()

create_sent_products_table()

def save_search_criteria(search_term, desired_size, desired_price, desired_condition, chat_id):
    conn = sqlite3.connect("search_criteria.db")
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO search_criteria (search_term, desired_size, desired_price, desired_condition, chat_id)
    VALUES (?, ?, ?, ?, ?)
    ''', (search_term, desired_size, float(desired_price), desired_condition, chat_id))

    search_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return search_id

def add_sent_product(search_id, url, title, size, condition, price):
    try:
        print(f"Adding product to DB: url={url}, title={title}, size={size}, condition={condition}, price={price}")
        print(
            f"Types: url={type(url)}, title={type(title)}, size={type(size)}, condition={type(condition)}, price={type(price)}")

        # Ensure that all fields except 'price' are either strings or None
        if not all(isinstance(param, (str, type(None))) for param in [url, title, size, condition]):
            raise ValueError("All fields except 'price' should be strings or None")

        if price is None:
            raise ValueError("Price cannot be None")

        conn = sqlite3.connect("sent_products.db")
        cursor = conn.cursor()

        cursor.execute('''
        INSERT OR IGNORE INTO sent_products (search_id, url, title, size, condition, price)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (search_id, url, title, size, condition, price))

        conn.commit()
        conn.close()
        print(f"Sent product added to database: {title}")
    except Exception as e:
        print(f"Error adding sent product to database: {e}")


def is_product_sent(url):
    try:
        conn = sqlite3.connect("sent_products.db")
        cursor = conn.cursor()

        cursor.execute('''
        SELECT 1 FROM sent_products WHERE url = ?
        ''', (url,))
        result = cursor.fetchone()

        conn.close()
        return result is not None
    except Exception as e:
        print(f"Error checking if product is sent: {e}")
        return False

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def send_telegram_notification(product_url, product_image):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"Matching Product: {product_url}")
        if product_image:
            await bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=product_image)
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

def loadCookies(driver, cookies_file):
    try:
        cookies = pickle.load(open(cookies_file, "rb"))
        for cookie in cookies:
            driver.add_cookie(cookie)
        driver.refresh()
    except FileNotFoundError:
        print("Cookies file not found. You need to log in.")
    except Exception as e:
        print(f"Error loading cookies: {e}")

def saveCookies(driver, cookies_file):
    pickle.dump(driver.get_cookies(), open(cookies_file, "wb"))

def parsePrice(price_string):
    try:
        price_string = price_string.replace('₺', '').replace('TL', '').replace(',', '').replace('.', '').strip()
        return float(price_string) if price_string else None
    except ValueError:
        return None


def normalizeSize(size):
    if '-' in size:
        size = size.split('-')[-1].strip()

    parts = re.split(r'\s*/\s*', size)

    normalized_parts = []
    for part in parts:
        match = re.match(r"([A-Za-z0-9]+)", part)
        if match:
            normalized_parts.append(match.group(1).upper())

    return "".join(normalized_parts)

async def scrape_and_notify(search_id, search_term, desired_size, desired_price, desired_condition, chat_id):
    driver = webdriver.Chrome()

    driver.get("https://dolap.com/giris")

    cookies_file = "cookies.pkl"
    loadCookies(driver, cookies_file)

    time.sleep(3)

    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="profileLink"]'))
        )
        print("Already logged in (using saved cookies).")
    except:
        print("Logging in using credentials...")

        usernameBox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="login-form"]/div[2]/input'))
        )

        passwordBox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="login-form"]/div[3]/input'))
        )

        loginButton = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="login-button"]'))
        )

        EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
        EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
        usernameBox.send_keys(EMAIL_USERNAME)
        passwordBox.send_keys(EMAIL_PASSWORD)
        loginButton.click()

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="profileLink"]'))
        )

        saveCookies(driver, cookies_file)

    time.sleep(2)

    currentPage = 1
    maxPage = 5

    search = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="search"]'))
    )
    search.send_keys(search_term)

    searchForm = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="header"]/div[1]/form'))
    )

    searchForm.submit()

    dropdown_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="main"]/div/div/div[2]/div[2]/div/div[1]/div[2]/span'))
    )

    dropdown_button.click()
    time.sleep(1)

    newest_to_oldest_option = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, '//span[@class=\'jcf-option\' and text()=\'Yeniden Eskiye\']'))
    )
    newest_to_oldest_option.click()

    time.sleep(2)

    while currentPage <= maxPage:
        print(f"Scraping page {currentPage}...")

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//*[@id=\"main\"]/div/div/div[2]/div[2]/div/div[1]/div[1]"))
        )

        products = driver.find_elements(By.XPATH, "//div[@class='col-xs-6 col-md-4']")
        matchingProductsLinks = []

        for i in range(len(products)):
            try:
                product = products[i]
                productLink = product.find_element(By.XPATH, ".//div[@class='img-block']//a[@rel='nofollow']")
                productUrl = productLink.get_attribute("href")

                if is_product_sent(productUrl):
                    print(f"Product {productUrl} already in the database. Skipping...")
                    continue

                print("Navigating to:", productUrl)

                driver.get(productUrl)

                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='detail-block']"))
                )

                sizeElement = driver.find_element(By.XPATH, "//div[@class='title-block']//h1")
                productSize = sizeElement.text.strip()

                conditionElement = driver.find_element(By.XPATH, "//div[@class='title-block']//span[@class='subtitle']")
                productCondition = conditionElement.text.strip()

                priceElement = driver.find_element(By.XPATH, "//*[@id=\"main\"]/div/div/div[1]/div[2]/div/div[2]/div[1]/span")
                productPrice = priceElement.text.strip()

                productImageElement = driver.find_element(By.XPATH, "//*[@id=\"main\"]/div/div/div[1]/div[1]/div/div[2]/div/ul/li[1]/a/img")
                productImageUrl = productImageElement.get_attribute("src")

                price = parsePrice(productPrice)

                if price is None:
                    print(f"Failed to parse price: {productPrice}")
                    continue

                normalized_desired_size = normalizeSize(desired_size)
                normalized_product_size = normalizeSize(productSize)

                print("product size" + normalized_product_size)
                print("desired" + normalized_desired_size)

                print("input price: " + desired_price)
                print("product price: " + str(price))

                if normalized_desired_size == normalized_product_size and desired_condition in productCondition and price <= float(desired_price):
                    print(f"Product matches! Size: {productSize}, Condition: {productCondition}, Price: {price}")
                    matchingProductsLinks.append(productUrl)

                    await send_telegram_notification(productUrl, productImageUrl)

                    add_sent_product(search_id, str(productUrl), productSize, normalized_product_size, productCondition, price)


                driver.back()

                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[@class='col-xs-6 col-md-4']"))
                )
                products = driver.find_elements(By.XPATH, "//div[@class='col-xs-6 col-md-4']")

            except Exception as e:
                print(f"Error processing product {i}: {e}")

        print(f"Matching product links for page {currentPage}:")
        for link in matchingProductsLinks:
            print(link)

        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//li[@class="next"]/a'))
            )
            next_button.click()
            currentPage += 1
            time.sleep(3)
        except Exception as e:
            print(f"Error navigating to the next page: {e}")
            break

    print("Scraping complete!")

async def start(update, context):
    await update.message.reply_text(
        "Welcome to the product search bot! Please provide your search criteria.\n"
        "Format: \nsearch: <product_name>, size: <desired_size>, price: <desired_price>, condition: <desired_condition>\n"
        "Example: search: kırmızı kazak, size: M Beden, price: 200, condition: Az Kullanılmış"
    )

async def handle_message(update, context):
    text = update.message.text
    chat_id = update.message.chat_id
    print(f"Received input: {text}")

    try:
        parts = text.split(',')
        search_term = parts[0].split(':')[1].strip()
        desired_size = parts[1].split(':')[1].strip()
        desired_price = parts[2].split(':')[1].strip()
        desired_condition = parts[3].split(':')[1].strip()

        search_id = save_search_criteria(search_term, desired_size, desired_price, desired_condition, chat_id)

        await scrape_and_notify(search_id, search_term, desired_size, desired_price, desired_condition, chat_id)

    except Exception as e:
        await update.message.reply_text(f"Error processing your input: {e}")

tgBot = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


tgBot.add_handler(CommandHandler("start", start))
tgBot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

tgBot.run_polling()


