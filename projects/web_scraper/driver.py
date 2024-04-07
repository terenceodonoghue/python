import csv
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from tools.config import get_config
from tools.logger import log, Level

SERVER = "http://localhost:9515"
TIMEOUT = 5


class Driver:
    def __init__(self, from_file: str):
        config = get_config(from_file)
        output = open(config["file"], "w")

        self.config = config
        self.writer = csv.writer(output)
        self.driver = webdriver.Remote(
            command_executor=SERVER, options=webdriver.ChromeOptions()
        )

    def run(self) -> int:
        self.driver.get(self.config["site"])
        for page in self.pages():
            if page is None:
                continue
            else:
                self.driver.get(page)

                index = 1
                while True:
                    items = []
                    try:
                        if self.config["load"]:
                            self.wait_for_invisible(self.config["load"])
                    except:
                        break

                    for item in self.items():
                        row = {}
                        for column, selector in self.config["data"].items():
                            try:
                                row[column] = item.find_element(
                                    By.CSS_SELECTOR, selector
                                ).text
                            except:
                                row[column] = ""

                        items.append(row.values())

                    log(
                        index=index,
                        level=Level.INFO,
                        message="Found " + str(items.__len__()) + " items",
                        url=page,
                    )

                    self.writer.writerows(items)
                    index += 1

                    try:
                        self.wait_for_clickable(self.config["next"])
                    except:
                        break

        self.driver.quit()
        return os.EX_OK

    def pages(self):
        return list(
            map(
                lambda a: a.get_attribute("href"),
                self.driver.find_elements(By.CSS_SELECTOR, self.config["page"]),
            )
        )

    def items(self):
        return self.driver.find_elements(By.CSS_SELECTOR, self.config["item"])

    def wait_for_clickable(self, selector):
        WebDriverWait(self.driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        ).click()

    def wait_for_invisible(self, selector):
        WebDriverWait(self.driver, TIMEOUT).until(
            EC.invisibility_of_element((By.CSS_SELECTOR, selector))
        )
