import os
from groq import Groq
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import markdownify
from json import dumps, loads
from time import sleep
import openai
import re

def extract_json(s):
    pattern = r"(\{.*?\})"
    match = re.search(pattern, s, re.DOTALL)

    if match:
        json_str = match.group(1)
        try:
            json_data = loads(json_str)
            return json_data
        except:
            print("Error: Failed to decode JSON.")
            return None
    else:
        print("Error: No JSON found.")
        return None

def query(message, llm_type="chatgpt"):

    if llm_type == "groq":
        client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )

        chat_completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": message}]
        )
        return chat_completion.choices[0].message.content
    
    elif llm_type == "chatgpt":
        openai.api_key = os.getenv("OPENAI_API_KEY")

        chat_completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": message}
            ]
        )
        return chat_completion.choices[0].message.content

def fetch_script(movie_name):
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
    name = driver.find_elements(By.TAG_NAME, "h1")[-1].text[:-7]
    read = driver.find_element(By.XPATH, "//a[contains(@href, '/scripts/')]").get_attribute(
        "href"
    )

    # Read script
    driver.get(read)
    td = driver.find_element(By.XPATH, "//td[contains(@class, 'scrtext')]")
    pre = td.find_element(By.XPATH, "./pre").get_attribute("innerHTML")
    driver.quit()

    h = markdownify.markdownify(pre, heading_style="ATX").replace("**", "")
    return {
        "name": name,
        "poster": poster,
        "html": h
    }

def rate(h):
    prior = "Does the above script portray"
    final = "YES, NO, or MAYBE. Answer using the following JSON format: {'answer': 'YES', 'explanation': 'This is why', 'examples': 'When...'}"

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
        response_json = None
        while response_json is None:
            response = query(h + "\n" + prior + " " + question + "? " + final)
            response_json = extract_json(response)
            data[question] = response_json
        with open("final.json", "w") as f:
            f.write(dumps(data))
        #sleep(60) - activate this if you need to impliment token minute limits
    
    return data

movie = fetch_script("Joker")
rating = rate(movie["html"])

with open("movies/" + movie["name"] + ".json", "w") as f:
    f.write(dumps({"metadata": movie, "rating": rating}))