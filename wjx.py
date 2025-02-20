import logging
import random
import re
import threading
import traceback
import json
import os
from threading import Thread
import time
import numpy
import requests
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

"""
    @Author:charowhite
    @Time:2025.2
    Modified for headless Ubuntu environment.
    Independent config file,
    separate control of page duration,
    Thanks to Zemelee/wjx project inspiration.
"""

# 全局状态变量
curCount = 0
curFail = 0
lock = threading.Lock()

# 配置文件路径
CONFIG_FILE = "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_fields = ['url', 'single_prob', 'multiple_prob', 'targetCount']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"缺少必要参数: {field}")
        
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件 {CONFIG_FILE} 未找到")
    except json.JSONDecodeError:
        raise ValueError("配置文件格式错误")

try:
    config = load_config()
except Exception as e:
    logging.critical(str(e))
    exit(1)

# 停留时间参数
base_page_delay = config.get('page_delay', 30)  # 默认30秒
min_delay = max(0, base_page_delay - 8)
max_delay = base_page_delay + 8

# 参数处理
url = config['url']
targetCount = config['targetCount']
topFail = config.get('topFail', 3)
thread_count = config.get('thread_count', 2)
useIp = config.get('useIp', False)
ip_api = config.get('ip_api', "")

# 题型概率参数处理
prob_config = {
    'single_prob': config.get('single_prob', {}),
    'droplist_prob': config.get('droplist_prob', {}),
    'multiple_prob': config.get('multiple_prob', {}),
    'matrix_prob': config.get('matrix_prob', {}),
    'scale_prob': config.get('scale_prob', {}),
    'texts': config.get('texts', {}),
    'texts_prob': config.get('texts_prob', {})
}

for prob_name in ['single_prob', 'matrix_prob', 'droplist_prob', 'scale_prob', 'texts_prob']:
    prob = prob_config[prob_name]
    for key in list(prob.keys()):
        if isinstance(prob[key], list) and prob[key] != -1:
            try:
                prob_sum = sum(prob[key])
                if prob_sum <= 0:
                    raise ValueError(f"{prob_name} 第{key}题概率和不能为0")
                prob[key] = [x / prob_sum for x in prob[key]]
            except:
                prob[key] = [1.0/len(prob[key])]*len(prob[key])

single_prob = list(prob_config['single_prob'].values())
droplist_prob = list(prob_config['droplist_prob'].values())
multiple_prob = list(prob_config['multiple_prob'].values())
matrix_prob = list(prob_config['matrix_prob'].values())
scale_prob = list(prob_config['scale_prob'].values())
texts = list(prob_config['texts'].values())
texts_prob = list(prob_config['texts_prob'].values())

def validate(ip):
    pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):(\d{1,5})$'
    return re.match(pattern, ip) is not None

def zanip():
    if not ip_api:
        return ""
    try:
        ip = requests.get(ip_api, timeout=10).text.strip()
        return ip if validate(ip) else ""
    except:
        return ""

def detect(driver):
    q_list = []
    pages = driver.find_elements(By.XPATH, '//*[@id="divQuestion"]/fieldset')
    for i in range(1, len(pages)+1):
        questions = driver.find_elements(By.XPATH, f'//*[@id="fieldset{i}"]/div')
        valid_count = sum(1 for q in questions if q.get_attribute("topic").isdigit())
        q_list.append(valid_count)
    return q_list

def vacant(driver, current, index):
    if index >= len(texts) or index >= len(texts_prob):
        return
    try:
        content = texts[index]
        p = texts_prob[index]
        text_index = numpy.random.choice(numpy.arange(len(p)), p=p)
        driver.find_element(By.CSS_SELECTOR, f'#q{current}').send_keys(content[text_index])
    except:
        pass

def single(driver, current, index):
    if index >= len(single_prob):
        return
    try:
        options = driver.find_elements(By.XPATH, f'//*[@id="div{current}"]/div[2]/div')
        p = single_prob[index]
        if p == -1:
            r = random.randint(1, len(options))
        else:
            r = numpy.random.choice(numpy.arange(1, len(options)+1), p=p)
        driver.find_element(By.CSS_SELECTOR, f'#div{current} > div.ui-controlgroup > div:nth-child({r})').click()
    except:
        pass

def droplist(driver, current, index):
    if index >= len(droplist_prob):
        return
    try:
        driver.find_element(By.CSS_SELECTOR, f"#select2-q{current}-container").click()
        time.sleep(0.3)
        options = driver.find_elements(By.XPATH, f"//*[@id='select2-q{current}-results']/li")
        p = droplist_prob[index]
        r = numpy.random.choice(numpy.arange(1, len(options)), p=p)
        driver.find_element(By.XPATH, f"//*[@id='select2-q{current}-results']/li[{r+1}]").click()
    except:
        pass

def multiple(driver, current, index):
    if index >= len(multiple_prob):
        return
    try:
        options = driver.find_elements(By.XPATH, f'//*[@id="div{current}"]/div[2]/div')
        p = multiple_prob[index]
        selected = []
        for _ in range(3):  # 最多重试3次
            selected = [numpy.random.choice([0,1], p=[1-(x/100), x/100]) for x in p]
            if sum(selected) > 0:
                break
        for idx, val in enumerate(selected):
            if val == 1:
                driver.find_element(By.CSS_SELECTOR, f'#div{current} > div.ui-controlgroup > div:nth-child({idx+1})').click()
    except:
        pass

def matrix(driver, current, index):
    if index >= len(matrix_prob):
        return index
    try:
        rows = driver.find_elements(By.XPATH, f'//*[@id="divRefTab{current}"]/tbody/tr')
        q_num = sum(1 for tr in rows if tr.get_attribute("rowindex"))
        
        for i in range(1, q_num+1):
            if index >= len(matrix_prob):
                break
            p = matrix_prob[index]
            cols = driver.find_elements(By.XPATH, f'//*[@id="drv{current}_{i}"]/td')
            if p == -1:
                opt = random.randint(2, len(cols))
            else:
                opt = numpy.random.choice(numpy.arange(2, len(cols)+1), p=p)
            driver.find_element(By.CSS_SELECTOR, f'#drv{current}_{i} > td:nth-child({opt})').click()
            index += 1
        return index
    except:
        return index

def reorder(driver, current):
    try:
        items = driver.find_elements(By.XPATH, f'//*[@id="div{current}"]/ul/li')
        for j in range(1, len(items)+1):
            choice = random.randint(j, len(items))
            driver.find_element(By.CSS_SELECTOR, f'#div{current} > ul > li:nth-child({choice})').click()
            time.sleep(0.2)
    except:
        pass

def scale(driver, current, index):
    if index >= len(scale_prob):
        return
    try:
        options = driver.find_elements(By.XPATH, f'//*[@id="div{current}"]/div[2]/div/ul/li')
        p = scale_prob[index]
        choice = numpy.random.choice(numpy.arange(1, len(options)+1), p=p) if p != -1 else random.randint(1, len(options))
        driver.find_element(By.CSS_SELECTOR, f'#div{current} > div.scale-div > div > ul > li:nth-child({choice})').click()
    except:
        pass

def submit(driver):
    time.sleep(1)
    try:
        driver.find_element(By.XPATH, '//*[@id="layui-layer1"]/div[3]/a').click()
        time.sleep(0.5)
    except:
        pass
    
    try:
        driver.find_element(By.XPATH, '//*[@id="SM_BTN_1"]').click()
        time.sleep(2)
    except:
        pass
    
    try:
        slider = driver.find_element(By.XPATH, '//*[@id="nc_1__scale_text"]/span')
        if "请按住滑块" in slider.text:
            ActionChains(driver).drag_and_drop_by_offset(
                driver.find_element(By.XPATH, '//*[@id="nc_1_n1z"]'),
                slider.size['width'], 0
            ).perform()
            time.sleep(1)
    except:
        pass

def brush(driver):
    try:
        q_list = detect(driver)
        current = 0
        counters = {
            'single': 0, 'vacant': 0, 'droplist': 0,
            'multiple': 0, 'matrix': 0, 'scale': 0
        }

        for page_idx, page_size in enumerate(q_list):
            for _ in range(page_size):
                current += 1
                q_type = driver.find_element(By.CSS_SELECTOR, f'#div{current}').get_attribute("type")

                if q_type in ["1", "2"]:
                    vacant(driver, current, counters['vacant'])
                    counters['vacant'] += 1
                elif q_type == "3":
                    single(driver, current, counters['single'])
                    counters['single'] += 1
                elif q_type == "4":
                    multiple(driver, current, counters['multiple'])
                    counters['multiple'] += 1
                elif q_type == "5":
                    scale(driver, current, counters['scale'])
                    counters['scale'] += 1
                elif q_type == "6":
                    counters['matrix'] = matrix(driver, current, counters['matrix'])
                elif q_type == "7":
                    droplist(driver, current, counters['droplist'])
                    counters['droplist'] += 1
                elif q_type == "8":
                    driver.find_element(By.CSS_SELECTOR, f'#q{current}').send_keys(str(random.randint(1,100)))
                elif q_type == "11":
                    reorder(driver, current)

            # 页面停留时间控制
            delay = random.randint(min_delay, max_delay)
            logging.info(f"页面{page_idx+1}停留时间: {delay}秒")
            time.sleep(delay)

            try:
                if page_idx < len(q_list)-1:
                    driver.find_element(By.CSS_SELECTOR, '#divNext').click()
                    time.sleep(0.5)
                else:
                    driver.find_element(By.XPATH, '//*[@id="ctlNext"]').click()
            except:
                pass

        submit(driver)
    except Exception as e:
        raise

def run_thread():
    global curCount, curFail  # 声明全局变量
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    while True:
        with lock:
            if curCount >= targetCount:
                return
        
        proxy_ip = zanip() if useIp else ""
        driver = None
        try:
            if proxy_ip:
                chrome_options.add_argument(f'--proxy-server={proxy_ip}')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_window_size(550, 650)
            
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.navigator.chrome = {runtime: {}, app: {}};
                '''
            })
            
            driver.get(url)
            original_url = driver.current_url
            brush(driver)
            time.sleep(3)
            
            if driver.current_url != original_url:
                with lock:
                    curCount += 1
                    print(f"[成功] 已提交 {curCount}/{targetCount} | 失败 {curFail} | {time.strftime('%H:%M:%S')}")
            
            driver.quit()
            
        except Exception as e:
            with lock:
                curFail += 1
                if curFail >= topFail:
                    logging.critical(f"失败超过阈值 {topFail}，终止程序")
                    os._exit(1)
            
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            time.sleep(random.uniform(1, 3))

if __name__ == "__main__":
    print(f"""
    问卷自动填写系统启动
    ===================
    目标份数: {targetCount}
    失败阈值: {topFail}
    使用代理: {'是' if useIp else '否'}
    线程数量: {thread_count}
    停留时间: {base_page_delay}
    """)
    
    threads = []
    for _ in range(thread_count):
        t = Thread(target=run_thread)
        t.daemon = True
        threads.append(t)
        t.start()
    
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n用户中断，正在退出...")
        exit(0)
    
    print(f"""
    任务完成
    ===================
    成功提交: {curCount}
    失败次数: {curFail}
    """)
