import os
from groq import Groq
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import markdownify
from json import dumps, loads
from time import sleep

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)


def query(message):
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": message}],
        model="llama3-8b-8192",
    )
    return chat_completion.choices[0].message.content

movie_name = "Joker"

options = webdriver.FirefoxOptions()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)
driver.get("https://imsdb.com/")

searchbox = driver.find_element(By.NAME, "search_query")
searchbox.send_keys(movie_name)
submit = driver.find_element(By.NAME, "submit")
submit.click()

wait = WebDriverWait(driver, 4)
wait.until(
    EC.presence_of_element_located(
        (By.XPATH, "//*[contains(text(), 'Search results for')]")
    )
)

title = driver.find_element(By.XPATH, "//*[contains(text(), 'Search results for')]")
parent = title.find_element(By.XPATH, "./..")
first = parent.find_element(By.XPATH, "./p")
link = first.find_element(By.XPATH, "./a")
value = link.get_attribute("href")

# Movie located, grabbing info
driver.get(value)
poster = driver.find_element(
    By.XPATH, "//img[contains(@src, 'https://www.imsdb.com/posters')]"
).get_attribute("src")
read = driver.find_element(By.XPATH, "//a[contains(@href, '/scripts/')]").get_attribute(
    "href"
)

# Read script
driver.get(read)
td = driver.find_element(By.XPATH, "//td[contains(@class, 'scrtext')]")
pre = td.find_element(By.XPATH, "./pre").get_attribute("innerHTML")
h = markdownify.markdownify(pre, heading_style="ATX").replace("**", "")

print(h)

prior = "Does the above script portray"
final = "YES, NO, or MAYBE. Answer using the following JSON format: {'answer': 'YES', 'explanation': 'This is why'.}"

questions = [
    "traditional gender roles, with men as protectors and provides, and women as nurturers and homemakers",
    "positive depiction of male authority figures (fathers, husbands) as wise and benevolent leaders",
    "emphasis on the importance of harmonious relationships between men and women based on mutual respect and support",
    "promotion of the nuclear family as the ideal social unit",
    "positive portrayal of fathers as authoritative figures guiding and mentoring their children",
    "depiction of the home as a place of security and refuge, with clear roles and responsibilities",
    "emphasis on concepts like honor, duty, and responsibility, particularly from a male perspective",
    "positive portrayal of modesty in dress and behavior, especially for women",
    "highlighting masculine virtues such as physical strength, moral courage, and perseverance",
    "recognition and celebration of men in positions of leadership within communities, churches, and organizations",
    "acknowledgment of sacrifices made by men for the betterment of their families and communities",
    "positive depiction of institutions that uphold patriarchal values, such as churches and fraternal organizations",
    "respect for traditional cultural practices and customs that uphold patriarchal norms",
    "accuracy in depicting historical patriarchal societies and their contributions to culture and civilization",
    "exploration of challenges to patriarchal values in modern society and their potential consequences",
]

data = {}
for question in questions:
    print(question)
    data[question] = query(h + "\n" + prior + " " + question + "? " + final)
    with open("final.json", "w") as f:
        f.write(dumps(data))
    sleep(60)

driver.quit()
