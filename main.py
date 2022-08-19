import numpy as np
from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
import selenium.webdriver.support.expected_conditions as EC
from typing import List

alphabet = "abcdefghijklmnopqrstuvwxyz"


def get_words(file="all_possible_words"):
    return np.loadtxt(file, dtype=str)


def rank_words(letters, words):
    common_words = get_words("words")

    occurrences = dict()
    for letter in letters:
        occurrences[letter] = 0

    for word in words:
        for letter in word:
            if letter in letters:
                occurrences[letter] += 1

    scores = dict()
    for word in words:
        scores[word] = 0
        unique_letters = [*set(word)]
        for letter in unique_letters:
            if letter in letters:
                scores[word] += occurrences[letter]

        if word in common_words:
            scores[word] *= 1.2

    return np.array(sorted(scores.items(), key=lambda x: x[1], reverse=True))[:, 0]


def get_deletions(words, correct_letters: List[str], misplaced_letters: List[str], incorrect_letters: List[str]):
    def should_delete(w):
        for i in range(5):
            if w[i] != correct_letters[i] and correct_letters[i] != '':
                return True
            if w[i] == misplaced_letters[i] and misplaced_letters[i] != '':
                return True
            if incorrect_letters[i] in w and incorrect_letters[i] != '':
                return True

        return False

    shoulds = []
    for word in words:
        shoulds.append(should_delete(word))

    return shoulds


def filter_words(ranked_words, correct_letters, misplaced_letters, incorrect_letters):
    filtered_words = np.delete(ranked_words, np.where(
        get_deletions(ranked_words, correct_letters, misplaced_letters, incorrect_letters)))

    return filtered_words


def get_guess(turn, filtered_words, correct_letters, misplaced_letters, incorrect_letters):
    if len(filtered_words) > 0:
        guess = filtered_words[0]

        check_words = np.delete(filtered_words, np.where(filtered_words == guess))

        if turn < 4 and len(check_words) >= 6 - turn:
            count = 0
            for i in range(min(len(check_words), 6 - turn)):
                place_similar = 0
                for j in range(5):
                    if guess[j] == check_words[i][j]:
                        place_similar += 1

                if place_similar >= 3:
                    count += 1

            check_letters = []
            if count >= 6 - turn:
                for word in filtered_words:
                    check_letters += list(set(guess).symmetric_difference(set(word)))

                check_letters = list(set(check_letters))

                ranked_similars = rank_words(check_letters, get_words("all_possible_words"))
                # print(check_letters)
                # print(ranked_similars)

                guess = ranked_similars[0]

        return guess
    else:
        return None


def main(mode):
    driver = None
    hasWaited = False

    if mode == 1:
        driver = webdriver.Firefox()
        driver.get("https://wordlegame.org/")
        driver.implicitly_wait(60000)

    won = False
    lost_words = []
    last_len = 0
    while True:
        if len(lost_words) != last_len:
            print(lost_words)
            last_len = len(lost_words)
            print("New game", won)

        words = get_words()
        ranked_words = rank_words(alphabet, words)

        correct_letters = [''] * 5
        misplaced_letters = [''] * 5
        incorrect_letters = [''] * 5

        if mode == 1 and won:
            WebDriverWait(driver, 1000000).until(EC.element_to_be_clickable((By.XPATH,
                                                                             '/html/body/div[1]/div/section[1]/div/div[1]/div/div[1]/div/div/div[6]/div[2]/div/div[3]/button'))).click()
        won = False

        for turn in range(6):
            ranked_words = filter_words(ranked_words, correct_letters, misplaced_letters, incorrect_letters)
            guess = get_guess(turn, ranked_words, correct_letters, misplaced_letters, incorrect_letters)

            if mode == 1 and guess is None:
                driver.find_element(By.XPATH, '/html/body/div[1]/div/section[1]/div/div[1]/div/div[1]/div/div/header/div[2]/button[2]').click()
                text = driver.find_element(By.XPATH, '/html/body/div[1]/div/section[1]/div/div[1]/div/div[1]/div/div/div[6]/div[2]/div/div[2]/span').text
                lost_words.append(text)
                WebDriverWait(driver, 1000000).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div/section[1]/div/div[1]/div/div[1]/div/div/div[6]/div[2]/div/div[3]/button'))).click()
                won = True
                break

            correct_letters = [''] * 5
            misplaced_letters = [''] * 5
            incorrect_letters = [''] * 5

            if mode == 0:
                print("Guess:", guess)
                c_indicies = [int(i) for i in str(input("Indicies of green letters: ")).strip().split()]
                m_indicies = [int(i) for i in str(input("Indicies of yellow letters: ")).strip().split()]

                for i in c_indicies:
                    correct_letters[i] = guess[i]

                for i in m_indicies:
                    misplaced_letters[i] = guess[i]

                for i in range(5):
                    if i not in c_indicies + m_indicies:
                        incorrect_letters[i] = guess[i]

            if mode == 1:
                WebDriverWait(driver, 1000000).until(EC.element_to_be_clickable(
                    (By.XPATH, '/html/body/div[1]/div/section[1]/div/div[1]/div/div[1]/div/div/div[4]/div[1]')))

                actions = ActionChains(driver)
                actions.send_keys(guess + Keys.RETURN)
                actions.perform()

                if not won:
                    # Wait longer than 10 seconds since you're getting occasional timeout
                    el = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.XPATH,
                                                        f"/html/body/div[1]/div/section[1]/div/div[1]/div/div[1]/div/div/div[4]/div[1]/div[{turn + 1}]/div[5]")))

                    wait = WebDriverWait(driver, 10)
                    wait.until(lambda d: 'letter-' in el.get_attribute('class'))

                    for i in range(5):
                        elem = driver.find_element(By.XPATH,
                                                   f"/html/body/div[1]/div/section[1]/div/div[1]/div/div[1]/div/div/div[4]/div[1]/div[{turn + 1}]/div[{i + 1}]")
                        if elem.value_of_css_property('background-color') == "rgb(121, 184, 81)":
                            correct_letters[i] = guess[i]
                        elif elem.value_of_css_property('background-color') == "rgb(164, 174, 196)":
                            incorrect_letters[i] = guess[i]
                        else:
                            misplaced_letters[i] = guess[i]

                    if '' not in correct_letters:
                        won = True

        if not won and mode == 1:
            elem = driver.find_element(By.XPATH, '/html/body/div[1]/div/section[1]/div/div[1]/div/div[1]/div/div/div[6]/div[2]/div/div[2]/span')
            lost_words.append(elem.text)

            WebDriverWait(driver, 1000000).until(EC.element_to_be_clickable((By.XPATH,
                                                                             '/html/body/div[1]/div/section[1]/div/div[1]/div/div[1]/div/div/div[6]/div[2]/div/div[3]/button'))).click()

main(1)
