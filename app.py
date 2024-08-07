from flask import Flask, render_template, request
from groq import Groq
from json import dumps, loads
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC  # Import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait  # Import WebDriverWait
from time import sleep
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import markdownify
import openai
import os
from random import randint
import threading

# sudo apt install -y chromium-chromedriver

browser = "Firefox"

app = Flask(__name__)

def extract_json(input_string):
    try:
        start_index = input_string.find('{')
        end_index = input_string.rfind('}')
        
        if start_index != -1 and end_index != -1 and end_index > start_index:
            s = input_string[start_index:end_index+1]
            s = s.replace("\'", "\"")

            return loads(s)
        else:
            return None
    except Exception as e:
        print(str(e))
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

def fetch_script(movie_name, log_file):
    global browser

    try:
        print("- loading IMSDB")

        driver = None
        if browser == "Chrome":

            # Set up Chrome options
            options = ChromeOptions()
            # Uncomment the next line to run in headless mode
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("start-maximized")
            options.add_argument("disable-infobars")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--remote-debugging-port=9222")

            # Set up the Chromium browser
            options.binary_location = "/usr/bin/chromium"

            # Set up the Chrome driver
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

        else:
            options = FirefoxOptions()
            options.add_argument("--headless")
            options.binary_location = "/usr/bin/firefox-esr"  # Path to the Firefox binary

            # Set up the Firefox driver
            service = FirefoxService()
            driver = webdriver.Firefox(service=service, options=options)

        driver.get("https://imsdb.com/")

        print("- searching...")
        searchbox = driver.find_element(By.NAME, "search_query")
        searchbox.send_keys(movie_name)
        submit = driver.find_element(By.NAME, "submit")
        submit.click()

        #  127.0.6533.88

        wait = WebDriverWait(driver, 4)
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(), 'Search results for')]")
            )
        )

        print("- handling results")
        title = driver.find_element(By.XPATH, "//*[contains(text(), 'Search results for')]")
        parent = title.find_element(By.XPATH, "./..")
        first = parent.find_element(By.XPATH, "./p")
        link = first.find_element(By.XPATH, "./a")
        value = link.get_attribute("href")

        # Movie located, grabbing info
        print("- located script")
        driver.get(value)
        poster = ""
        try:
            poster = driver.find_element(
                By.XPATH, "//img[contains(@src, 'https://www.imsdb.com/posters')]"
            )
            if (poster != None):
                poster = poster.get_attribute("src")

        except Exception as e:
            print(str(e))
            with open(log_file, "w") as f:
                f.write("Poster not found (but we're still searching)...")

        print("- Ignoring poster...")

        film = driver.find_elements(By.TAG_NAME, "h1")[-1].text[:-7]
        read = driver.find_element(By.XPATH, "//a[contains(@href, '/scripts/')]").get_attribute(
            "href"
        )

        # Read script
        print("- read script")
        driver.get(read)
        td = driver.find_element(By.XPATH, "//td[contains(@class, 'scrtext')]")
        pre = td.find_element(By.XPATH, "./pre").get_attribute("innerHTML")
        driver.quit()

        print("- closing Selenium")
        h = markdownify.markdownify(pre, heading_style="ATX").replace("**", "")
        return {
            "film": film,
            "poster": poster,
            "html": h
        }
    except Exception as e:
        with open(log_file, "w") as f:
            f.write("Error: " + str(e))
        return None

def new_job(movie_string, id, movie_path):
    try:
        print("Starting new job...")

        log_file = "status/" + str(id)
        with open(log_file, "w") as f:
            f.write("Searching for the script online...")

        movie = fetch_script(movie_string, log_file)
        if movie == None:
            return

        try:
            prior = "Does the above script portray"
            final = "YES, NO, or MAYBE. Answer using the following JSON format: {'answer': 'YES', 'explanation': 'This is why', 'examples': 'When...'}"

            questions = [
                ["Traditional Gender Roles", "traditional gender roles, with men as protectors and provides, and women as nurturers and homemakers"],
                ["Positive Masculinity", "positive depiction of male authority figures (fathers, husbands) as wise and benevolent leaders"],
                ["Respectful Interactions Between Men & Women", "emphasis on the importance of harmonious relationships between men and women based on mutual respect and support"],
                ["Respect for the Family Unit", "promotion of the nuclear family as the ideal social unit"],
                ["Positive Fatherhood", "positive portrayal of fathers as authoritative figures guiding and mentoring their children"],
                ["Respect of the Household", "depiction of the home as a place of security and refuge, with clear roles and responsibilities"],
                ["Honor, Duty, & Responsibility", "emphasis on concepts like honor, duty, and responsibility, particularly from a male perspective"],
                ["Modesty", "positive portrayal of modesty in dress and behavior, especially for women"],
                ["Positive Male Leadership", "recognition and celebration of men in positions of leadership within communities, churches, and organizations"],
                ["Acknowledgment of Male Sacrifice", "acknowledgment of sacrifices made by men for the betterment of their families and communities"],
                ["Respect for Churches & Institutions", "positive depiction of institutions that uphold patriarchal values, such as churches and fraternal organizations"],
                ["Respect for Cultural Values", "respect for traditional cultural practices and customs that uphold patriarchal norms"],
                ["Historical Accuracy", "accuracy in depicting historical patriarchal societies and their contributions to culture and civilization"],
                ["Exploration of Contemporary Challenges", "exploration of challenges to patriarchal values in modern society and their potential consequences"],
            ]

            questions_count = len(questions)

            rating = {}
            question_index = 0
            for question_pair in questions:
                question_index += 1

                with open(log_file, "w") as f:
                    f.write("Handling question " + str(question_index) + "/" + str(questions_count) + "...")

                question_title = question_pair[0]
                question = question_pair[1]

                print(question)
                response_json = None
                attempts = 0
                while response_json is None and attempts < 3:
                    attempts += 1
                    response = query(movie["html"] + "\n" + prior + " " + question + "? " + final)
                    response_json = extract_json(response)
                    rating[question_title] = response_json
                    print(response)

            # Cache answer for later
            print("Saving...")
            with open(movie_path, "w") as f:
                f.write(dumps({"metadata": movie, "rating": rating, "success": 1}))

        except Exception as e:
            print(str(e))

    except Exception as e:
        print(str(e))

    os.remove(log_file)
    return

@app.route("/reelvalues", methods=["GET"])
def main():
    sample = [film.replace(".json", "") for film in os.listdir("movies")]
    if len(sample) > 10:
        sample = sample[:10]
    return render_template("index.html", sample=sample)

@app.route("/reelvalues", methods=["POST"])
def fetch():
    route = request.form.get("route")
    movie_string = request.form.get("film")
    movie_path = "movies/" + movie_string + ".json"

    if (route == "status"):
        sleep(1)

        path = "status/" + str(request.form.get("id"))
        if os.path.exists(path):
            message = ""
            with open(path, "r") as f:
                message = f.read()
            return {
                "success": 3,
                "message": message
            }

        else:
            if (os.path.exists(movie_path)):
                with open(movie_path, "r") as f:
                    data = loads(f.read())

                    count = 0
                    score = 0
                    for r in data["rating"]:
                        if data["rating"][r] != None:
                            count += 1
                            if data["rating"][r]["answer"] == "YES":
                                score += 1
                            elif data["rating"][r]["answer"] == "MAYBE":
                                score += 0.5

                    return {
                        "film": data["metadata"]["film"],
                        "poster": data["metadata"]["poster"],
                        "rating": data["rating"],
                        "score": int((score / count) * 100),
                        "success": 1
                    }
            
            else:
                return {
                    "success": 2
                }
        
    elif (route == "search"):

        # If exists, just use that smh
        if (os.path.exists(movie_path)):
            with open(movie_path, "r") as f:
                data = loads(f.read())

                count = 0
                score = 0
                for r in data["rating"]:
                    if data["rating"][r] != None:
                        count += 1
                        if data["rating"][r]["answer"] == "YES":
                            score += 1
                        elif data["rating"][r]["answer"] == "MAYBE":
                            score += 0.5

                return {
                    "film": data["metadata"]["film"],
                    "poster": data["metadata"]["poster"],
                    "rating": data["rating"],
                    "score": int((score / count) * 100),
                    "success": 1
                }
            
        else:

            id = randint(0, 9999)
            while os.path.exists("status/" + str(id)):
                id = randint(0, 9999)

            with open("status/" + str(id), "w") as f:
                f.write("Starting new thread...")
            
            thread = threading.Thread(target=lambda: new_job(movie_string, id, movie_path))
            thread.start()

            return {
                "success": 1,
                "id": id
            }