import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service

#创建一个目录来存储图像
def create_directory(url):
    folder_name = url.split("//")[1].replace("/", "_")
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name

def get_partial_snapshot(driver,cord,width,height):
    x = cord['x']
    y = cord['y']
    driver.save_screenshot('tmp.png')


def get_cord(driver:webdriver.Edge(),elem):#通过js获取元素相对于视口位置
    js = '''
        var element = arguments[0]
        if (element) {
            let rect = element.getBoundingClientRect();
            return {x: rect.left, y: rect.top};
        } else {
            
            return {x: -1,y: -1};
        }'''
    #elem_xpath = elem.get_attribute('xpath')
    return driver.execute_script(js,elem)

def is_elem_in_window(driver: webdriver.Edge,element):#判断元素是否在视口范围内且可视
    windowsize = driver.get_window_size()
    elem_location = get_cord(driver,element)
    if elem_location['x']>0 and elem_location['x']<windowsize['width'] and elem_location['y']>0 and elem_location['y']<windowsize['height'] and element.is_displayed():
        return True
    else:
        return False


def scroll_webpage(driver,height):
    driver.execute_script("window.scrollBy(0, "+str(height)+");")

def check_img(driver,img):
    top_zone = 150
    cord = get_cord(driver,img)
    size_x, size_y = img.size['width'], img.size['height']
    if size_x<50 and size_y <50:
        return False
    if cord['y']<top_zone:
        return False
    return True


def save_float_img(driver, folder_name,imgs,scroll_height):
    test = driver.find_element(By.XPATH,'''//*[@id="csdn-toolbar"]/div/div/div[1]/div/a/img''')
    print(test)
    print(get_cord(driver,test))
    current_num = 0
    float_lst = list()
    former = list()
    former_bak = list()
    current_height = 0
    webpage_height = driver.execute_script("return document.body.scrollHeight")

    while current_height<webpage_height:
        print(is_elem_in_window(driver,test))
        print(test in imgs)
        for img in imgs:
            if is_elem_in_window(driver,img):
                if img in former:
                    imgs.remove(img)
                    float_lst.append(img)
                else:
                    former_bak.append(img)
        former.clear()
        former = former_bak.copy()
        former_bak.clear()
        scroll_webpage(driver,scroll_height)
        current_height+=scroll_height

    for img in float_lst:
        cord = get_cord(driver,img)
        size_x, size_y = img.size['width'], img.size['height']
        if check_img(driver,img):
            src = img.get_attribute('src')
            img_data = img.screenshot_as_png
            with open(f'{folder_name}/{current_num+1}.png', 'wb') as f:
                f.write(img_data)
            current_num+=1
        
    return current_num

        


if __name__ == "__main__":
    # 从文本文件读取网址
    window_width = 1920
    window_height = 1080
    with open('urls.txt', 'r') as f:
        urls = f.read().splitlines()

    # 创建Driver
    edge_drive_path = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedgedriver.exe'
    svc = Service('C:/Program Files (x86)/Microsoft/Edge/Application/msedgedriver.exe')
    optn = webdriver.EdgeOptions()
    #optn.add_argument('--headless')
    driver = webdriver.Edge(service=svc,options=optn)

    for url in urls:
        driver.get(url)
        folder_name = create_directory(url)
        initial_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(window_width, window_height)

        total_visible_images = 0
        """ if(initial_height>(3*window_height)):
            scroll_height = initial_height//2
        else:
            scroll_height = window_height//2 """
        scroll_height = 0
        time.sleep(3)
        imgs = driver.find_elements(By.TAG_NAME, 'img')
        float_img_count=save_float_img(driver,folder_name,imgs,window_height)
        print(f"Total float AD images for {url}: {float_img_count}")

    #关闭浏览器
    driver.quit()