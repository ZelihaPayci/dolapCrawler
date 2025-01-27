import pickle
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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

    usernameBox.send_keys("")
    passwordBox.send_keys("")
    loginButton.click()

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="profileLink"]'))
    )

    saveCookies(driver, cookies_file)

time.sleep(2)

search = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, '//*[@id="search"]'))
)

search.send_keys("kırmızı kazak")

searchForm = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, '//*[@id="header"]/div[1]/form'))
)

searchForm.submit()

productNumber = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, '//*[@id="main"]/div/div/div[2]/div[2]/div/div[1]/div[1]/span'))
)
products = driver.find_elements(By.XPATH, "//div[@class=\"col-xs-6 col-md-4\"]")

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

        # Extract size and condition from the product page
        sizeElement = driver.find_element(By.XPATH, "//div[@class='title-block']//h1")
        productSize = sizeElement.text.strip()

        conditionElement = driver.find_element(By.XPATH, "//div[@class='title-block']//span[@class='subtitle']")
        productCondition = conditionElement.text.strip()

        if desiredSize in productSize and desiredCondition in productCondition:
            print(f"Product matches! Size: {productSize}, Condition: {productCondition}")
            matchingProductsLinks.append(productUrl)

        driver.back()

        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[@class='col-xs-6 col-md-4']"))
        )
        products = driver.find_elements(By.XPATH, "//div[@class='col-xs-6 col-md-4']")

    except Exception as e:
        print(f"Error processing product {i}: {e}")

print("Matching product links:")
for link in matchingProductsLinks:
    print(link)