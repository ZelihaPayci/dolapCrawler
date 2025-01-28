import pickle
import time
import asyncio

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telegram import Bot

TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
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

async def scrape_and_notify():
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

        usernameBox.send_keys("zelihapayci377@gmail.com")
        passwordBox.send_keys("Ay!szK1992")
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
    search.send_keys("kırmızı kazak")

    searchForm = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="header"]/div[1]/form'))
    )

    searchForm.submit()

    while currentPage <= maxPage:
        print(f"Scraping page {currentPage}...")

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//*[@id=\"main\"]/div/div/div[2]/div[2]/div/div[1]/div[1]"))
        )

        products = driver.find_elements(By.XPATH, "//div[@class='col-xs-6 col-md-4']")
        matchingProductsLinks = []

        desiredSize = "M Beden"
        desiredCondition = "Az Kullanılmış"

        for i in range(len(products)):
            try:
                product = products[i]
                productLink = product.find_element(By.XPATH, ".//div[@class='img-block']//a[@rel='nofollow']")
                productUrl = productLink.get_attribute("href")

                print("Navigating to:", productUrl)

                driver.get(productUrl)

                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='detail-block']"))
                )

                sizeElement = driver.find_element(By.XPATH, "//div[@class='title-block']//h1")
                productSize = sizeElement.text.strip()

                conditionElement = driver.find_element(By.XPATH, "//div[@class='title-block']//span[@class='subtitle']")
                productCondition = conditionElement.text.strip()

                productImageElement = driver.find_element(By.XPATH, "//*[@id=\"main\"]/div/div/div[1]/div[1]/div/div[2]/div/ul/li[1]/a/img")
                productImageUrl = productImageElement.get_attribute("src")

                if desiredSize in productSize and desiredCondition in productCondition:
                    print(f"Product matches! Size: {productSize}, Condition: {productCondition}")
                    matchingProductsLinks.append(productUrl)

                    # Await the Telegram notification function
                    await send_telegram_notification(productUrl, productImageUrl)

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
                EC.element_to_be_clickable((By.XPATH, '//*[@id="main"]/div/div/div[2]/div[2]/div/ul[2]/li[8]/a'))
            )
            next_button.click()
            currentPage += 1
            time.sleep(3)
        except Exception as e:
            print(f"Error navigating to the next page: {e}")
            break

    print("Scraping complete!")

if __name__ == "__main__":
    asyncio.run(scrape_and_notify())
