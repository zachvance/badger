"""
Script: LinkedIn Skill Assessment Quiz Bot
Description: A Python script that automates the process of taking LinkedIn Skill Assessment quizes.

This bot utilizes Selenium for logging into LinkedIn and collecting data for quiz questions, in conjuction with
PyAutoGUI and OpenCV for interacting with ChatGPT via the free version of chat.openai.com. All testing was done using
GPT 3.5.

Please note that there is still a chance of not passing a quiz with this bot - on the quizes I tested, it would usually
score perfect on the practices, and score in the top 30% on the real test... but I also had 2 results where it scored in
bottom 30%.

Setup:
- Fill out the config.py file
- This bot is using the Firefox webdriver, so you should have Firefox installed.
- Ensure you have an OpenAI account and are logged in. Opening your browser and navigating to "chat.openai.com" should
  yield the chat interface page, and not prompt you for a login or redirect you.
- Once the bot is run, it may require one more piece of additional input from the user to complete the captcha while
  logging into LinkedIn. You do not have to click the "VERIFY" button; you DO have to click the correct images when
  asked.

Todo:
    - Refactor so user can pass a list of quiz names to complete instead of just one quiz at a time
    - Account for users not being prompted for verification when logging in on LinkedIn... I can't test this properly
      at the moment, though, since I am always prompted to verify.
"""

import difflib
import itertools
import subprocess
import time

import cv2
import numpy as np
import pyautogui
import pyperclip
import selenium.common.exceptions
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from config import EMAIL, PASSWORD, QUIZ_TO_COMPLETE, PRACTICE, RESPONSE_DELAY


class Bot:
    def __init__(self):
        self.practice = PRACTICE
        self.driver = webdriver.Firefox()
        self.wait = WebDriverWait(self.driver, 10)
        self.quizes = [QUIZ_TO_COMPLETE]
        self.email = EMAIL
        self.password = PASSWORD

        self.current_quiz = None
        self.current_question = None
        self.current_response = None
        self.codeblock = None
        self.possible_answers = []
        self.possible_answers_text = []
        self.answer_dict = None
        self.response_delay = RESPONSE_DELAY  # Time in seconds to wait for GPT's answer
        self.conversation_transcript = []

        self.snap_window()

    def set_current_quiz(self) -> None:
        """
        Sets the current quiz to the first quiz in the list of available quizzes and removes it from the list.

        If the list of available quizzes is empty, sets the current quiz to None.

        :return: None
        :rtype: None
        :raises: IndexError if the list of available quizzes is empty
        """
        try:
            self.current_quiz = self.quizes.pop(0)
        except IndexError:
            self.current_quiz = None

    def build_hyperlink(self, quiz: str) -> str:
        """
        Builds a hyperlink to a LinkedIn skill assessment quiz, using the provided quiz name.

        :param quiz: The name of the quiz to build the hyperlink for.
        :type quiz: str

        :return: A hyperlink to the specified quiz on LinkedIn.
        :rtype: str
        """
        encoded_quiz = quiz.replace(" ", "%20")
        link_start = "https://www.linkedin.com/skill-assessments/"
        mode = "?normal_mode"

        if self.practice:
            mode = "?practiceModal=&practiceMode=true"

        return f"{link_start}{encoded_quiz}{mode}"

    def check_exists_by_xpath(self, xpath) -> bool:
        """
        Checks if an element exists on the page using an XPath expression. Not in use.

        :param xpath: A string representing the XPath expression to use.
        :return: True if the element exists, False otherwise.
        """
        return bool(self.driver.find_element("xpath", xpath))

    def login_to_linkedin(self) -> None:
        """
        Logs in to LinkedIn using the email and password provided to the constructor.

        :return: None
        """
        self.driver.get("https://www.linkedin.com")
        self.driver.find_element_by_name("session_key").send_keys(self.email)
        self.driver.find_element_by_name("session_password").send_keys(self.password)
        self.driver.find_element_by_xpath("/html/body/main/section[1]/div/div/form[1]/div[2]/button").click()

    def snap_window(self, right=True) -> None:
        """
        Snap the current window to the top and either the right or left side of the screen. Note that the duplicated
        is intentional - as it seems to fix positioning errors that were encountered when using a multi-monitor setup.

        :param right: If True (default), snap the window to the right side of the screen. If False, snap the window to the left side of the screen.
        :type right: bool

        :return: None

        :raises: None
        """
        pyautogui.hotkey("win", "up")
        pyautogui.hotkey("win", "up")
        time.sleep(0.05)
        if right:
            pyautogui.hotkey("win", "right")
        else:
            pyautogui.hotkey("win", "left")

    def find_and_click_image(self, image_path, offsets=(0, 0)) -> tuple[int, int]:
        """
        Find and click on an images on the screen.

        :param image_path: A string representing the path to the images file to be searched for.
        :type image_path: str
        :param offsets: A tuple containing the x and y offsets to be added to the center of the images. Defaults to (0, 0).
        :type offsets: tuple
        :return: A tuple containing the x and y coordinates of the center of the clicked images.
        :rtype: tuple
        :raises: TypeError, ValueError

        This method searches for an images on the screen, clicks on its center, and returns the coordinates of the clicked position.
        The images to be searched for is specified by the `image_path` argument, which should be a string representing the path
        to the images file.

        The `offsets` argument is an optional tuple containing the x and y offsets to be added to the center of the images before
        clicking. This is useful if you need to click on a specific point within the images rather than the center. The default
        value is (0, 0), which means that the click will be on the center of the images.

        If the specified images is not found on the screen, a ``ValueError`` will be raised. If the arguments are of an invalid
        type or format, a ``TypeError`` will be raised.
        """

        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        screenshot = pyautogui.screenshot()
        screenshot_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)

        result = cv2.matchTemplate(screenshot_gray, image, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        x = max_loc[0] + image.shape[1] // 2 + offsets[0]
        y = max_loc[1] + image.shape[0] // 2 + offsets[1]

        pyautogui.click(x, y)
        return (x, y)

    def navigate_to_quizes(self):
        self.login_to_linkedin()

        # Todo: I wanted to switch this to a wait but the elements won't stay on the screen long enough for me to
        #       get their info - if you take too long, you get redirected.
        time.sleep(7)  # Wait for the verification to pop up

        self.find_and_click_image(
            "images\\verify_button_linkedin.png"
        )
        time.sleep(10)  # Wait for the user to complete the captcha

        # self.driver.get(self.build_hyperlink(self.quizes[0]))  # Going directly to the hyperlinks doesn't seem to work
        self.driver.get("https://www.linkedin.com/skill-assessments/")

        # Go to the search (requires slight delays after each action)
        self.wait.until(
            EC.element_to_be_clickable(("css selector", ".search-basic-typeahead"))
        ).click()  # Search
        time.sleep(0.5)
        pyautogui.typewrite(self.current_quiz)
        time.sleep(1)

        self.find_and_click_image(
            "images\\linkedin_skill_search.png", offsets=(0, 50)
        )

        if self.practice:
            self.wait.until(
                EC.element_to_be_clickable(("xpath", "//*[@title='Practice']"))
            ).click()  # Practice
            self.wait.until(
                EC.element_to_be_clickable(
                    (
                        "xpath",
                        "/html/body/div[3]/div/div/div[2]/section/footer/div/button[2]/span",
                    )
                )
            ).click()  # Next
            time.sleep(3)
        else:
            self.wait.until(
                EC.element_to_be_clickable(("xpath", "//*[@title='Start']"))
            ).click()  # Start
            time.sleep(3)

    def navigate_to_chat(self) -> None:
        """
        Opens the chat.openai.com website in a new tab of the Firefox browser, and snaps the browser window to the left
        half of the screen.

        :return: None
        """
        url = "https://chat.openai.com"
        browser_path = "C:\\Program Files\\Mozilla Firefox\\Firefox.exe"
        subprocess.Popen([browser_path, "-new-tab", url])
        time.sleep(1)
        self.snap_window(right=False)

    def parse_question(self) -> None:
        question_text = self.driver.find_element(
            "css selector", ".sa-assessment-quiz__multi-line"
        ).text
        question_text = question_text.split("\n")
        question_text = question_text[0].strip()
        self.current_question = question_text

        if bool(self.driver.find_element("xpath", "/html/body/div[5]/div[3]/div[2]/div/div/main/div/section/div[1]/div[1]/div/p/span[1]")):
            codeblock = self.driver.find_element(
                "xpath",
                "/html/body/div[5]/div[3]/div[2]/div/div/main/div/section/div[1]/div[1]/div/p/span[1]",
            ).text
            codeblock = codeblock.split("\n")
            codeblock = " ".join(codeblock)
            self.codeblock = codeblock

        time.sleep(1)

        self.possible_answers = [
            self.driver.find_element("css selector", f"#skill-assessment-quiz-{i}")
            for i in range(4)
        ]

        time.sleep(1)

        self.possible_answers_text = []
        for a in self.possible_answers:
            t = a.text
            t = t.split("\n")
            t = " ".join(t)
            self.possible_answers_text.append(t)

        time.sleep(1)

        self.answer_dict = {
            "A": self.possible_answers[0],
            "B": self.possible_answers[1],
            "C": self.possible_answers[2],
            "D": self.possible_answers[3],
        }

    def ask_question(self) -> None:
        self.find_and_click_image("images\\send_a_message.png")
        answers = self.possible_answers_text
        if self.codeblock:
            q = f"Here is a multiple choice question about {self.current_quiz}: {self.current_question} {self.codeblock} The possible answers are A) {answers[0]}, B) {answers[1]}, C) {answers[2]}, or D) {answers[3]}. Which answer is the most correct? Respond only with a single-letter answer and no punctuation. Your answer must be a single-letter; your response cannot be more than 1 character in length."
        else:
            q = f"Here is a multiple choice question about {self.current_quiz}: {self.current_question} The possible answers are A) {answers[0]}, B) {answers[1]}, C) {answers[2]}, or D) {answers[3]}. Which answer is the most correct? Respond only with a single-letter answer and no punctuation. Your answer must be a single-letter.; your response cannot be more than 1 character in length."

        pyautogui.typewrite(q)
        pyautogui.press("enter")
        self.conversation_transcript.append(q)

        # Wait for response from GPT
        time.sleep(self.response_delay)

    def parse_response(self) -> None:
        """
        Parses the response from the current quiz question.

        The method finds and clicks on the response images, then copies the response text to the clipboard and
        removes any dots and capitalizes it. If the response length is greater than 1, the method attempts to
        parse the answer letter from the response sentence. The parsed response is stored in the `current_response`
        attribute.

        :return: None
        :rtype: None
        """
        x, y = self.find_and_click_image("images\\response.png")

        # Copy the response
        pyautogui.tripleClick(x + 50, y)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.01)
        response = pyperclip.paste()
        response = response.replace(".", "").upper()
        self.current_response = response

        # Test response length; if lober than 1, attempt to parse the answer letter from the sentence.
        # (This is precautionary as occasionally GPT will still give the answer in a sentence)
        if len(response) > 1:
            response = response.replace('"', "")
            response = [word for word in response.split() if len(word) == 1][0]
            self.current_response = response

    def select_answer(self) -> None:
        """
        Selects the answer option corresponding to the current response in the quiz.

        :raises KeyError: If the current response is not one of "A", "B", "C", or "D", or if the corresponding answer
            option is not found in the `answer_dict` dictionary.
        :returns: None

        This method uses the current response letter to determine the index of the answer option in the
        `possible_answers_text` list, and adds a transcript of the selected answer to the `conversation_transcript`
        list. It then clicks the corresponding answer option using the `answer_dict` dictionary and the Selenium
        `execute_script` method.
        """

        index = ord(self.current_response) - ord("A")
        answer_option = self.possible_answers_text[index]
        self.conversation_transcript.append(f"{self.current_response} - {answer_option}")
        self.driver.execute_script("arguments[0].click();", self.answer_dict[self.current_response])

    def match_response(self) -> None:
        """Not in use. Originally used because I was getting an organic answer from GPT and then matching it with the
        multiple choice answer it was closest to. I've since opted to provide GPT with the possible answers, which I
        think gives more direction and less chance for error. I've left this method here, since it did work and is
        still viable, but it would require refactoring to make it function again."""

        # Match the most correct one
        current_answer = None
        current_similarity = 0.00
        for item in possible_answers:
            similarity = difflib.SequenceMatcher(None, item.text, response).ratio()
            print(f"{item.text} similarity is {similarity}")
            print('-'*80)

            if similarity > current_similarity:
                current_answer = item
                current_similarity = similarity

        # print(f"The most probable answer is '{current_answer.text}'.")
        # di[current_answer].click()

        # di[response].click()  # Sometimes there were issues with click(), the line below seems to solve them
        driver.execute_script("arguments[0].click();", di[response])

    def submit_answer(self) -> None:
        """
        Submit the answer for the current question.

        :param driver: The webdriver object.
        :type driver: selenium.webdriver.Firefox
        :param practice: A boolean value indicating whether the current question is a practice question or not.
        :type practice: bool
        """
        if self.practice:
            # Click "Check answer" and "Next" buttons for practice questions
            self.driver.find_element(
                "xpath",
                "/html/body/div[5]/div[3]/div[2]/div/div/main/div/section/footer/div/button/span",
            ).click()
            time.sleep(0.5)
            self.driver.find_element(
                "xpath",
                "/html/body/div[5]/div[3]/div[2]/div/div/main/div/section/footer/div/button/span",
            ).click()
        else:
            # Click "Submit" button for graded questions
            self.driver.find_element(
                "xpath",
                "/html/body/div[5]/div[3]/div[2]/div/div/main/div/section/footer/div/button/span",
            ).click()

    def refresh_window(self) -> None:
        """
        Refreshes the active window by simulating the 'F5' key press using PyAutoGUI.

        This function waits for 3 seconds after simulating the key press to allow the window to fully refresh.

        :return: None
        """
        pyautogui.press("f5")
        time.sleep(3)

    def answer_quiz_questions(self) -> None:
        num = 2 if self.practice else 15
        for i in range(num):
            self.parse_question()
            self.ask_question()
            self.parse_response()
            self.select_answer()
            self.submit_answer()
            self.refresh_window()

    def run(self) -> None:
        self.navigate_to_chat()
        self.set_current_quiz()
        self.navigate_to_quizes()
        self.answer_quiz_questions()
        self.save_transcript()

    def save_transcript(self) -> None:
        """
        Saves the conversation transcript to a file in the current directory with the name "<quiz-name>-transcript.txt".

        :return: None
        """
        with open(f"{self.current_quiz}-transcript.txt", "w") as f:
            for item in self.conversation_transcript:
                f.write(f"{item}\n")


if __name__ == "__main__":
    bot = Bot()
    bot.run()
