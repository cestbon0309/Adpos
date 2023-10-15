import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import hashlib
import urllib.parse as urlparse
import cv2
import csv
import xlwt
import argparse

#创建一个目录来存储图像
def create_directory(url):
    print(f'CREATING FOLDER FOR {url}')
    if url == '':
        print('invalid url!')
        return None

    parsed_url = urlparse.urlparse(url)
    print(parsed_url)
    host = parsed_url.netloc
    hash_object = hashlib.sha256((parsed_url.netloc+parsed_url.path).encode())
    # 对网址哈希，防止文件夹重名
    hash_hex = hash_object.hexdigest()[:8]
    # 构建最终的文件夹名
    folder_name = host + '_' + hash_hex
    print(folder_name)
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name

def get_elem_screenshot(driver: webdriver.Edge,element):
    image = None
    try:
        w_size = driver.get_window_size()
        w_width,w_height = w_size['width'],w_size['height']
        cord = get_cord(driver,element)
        size_x, size_y = element.size['width'], element.size['height']
        startx,starty = int(cord['x'] - size_x//2),int(cord['y'] - size_y//2)
        endx,endy = int(cord['x'] + 1.5*size_x) , int(cord['y']+ 1.5*size_y)
        startx = startx if startx >= 0 else 0
        starty = starty if starty >= 0 else 0
        endx = endx if endx <= w_width else w_width
        endy = endy if endy <= w_height else w_height
        screenshot = driver.save_screenshot('snp_tmp.png')
        image = cv2.imread('snp_tmp.png')
        image = image[starty:endy,startx:endx]
        os.remove('snp_tmp.png')
        


    except Exception as e:
        print(f'ERROR: failed to take screenshot {e}')
        pass

    return image


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
    current_num = 0
    float_lst = list()
    float_screenshots = []
    former = list()
    former_bak = list()
    current_height = 0
    webpage_height = driver.execute_script("return document.body.scrollHeight")
    while current_height<webpage_height-1080:

        for img in imgs:
            if is_elem_in_window(driver,img):
                if img in former:
                    float_screenshots.append(get_elem_screenshot(driver,img)) 
                    imgs.remove(img)
                    float_lst.append(img)
                else:
                    former_bak.append(img)
        former.clear()
        former = former_bak.copy()
        former_bak.clear()
        scroll_webpage(driver,scroll_height)
        current_height+=scroll_height
    info_xls = xlwt.Workbook(encoding='UTF-8')
    sheet = info_xls.add_sheet('img_infos')
    sheet.write(0,0,'src')
    sheet.write(0,1,'size')
    sheet.write(0,2,'pos')
    sheet.write(0,3,'inner_id')
    sheet.write(0,4,'valid')
    sheet.write(0,5,'advertisement')
    current_line = 1
    for img in float_lst:
        screenshot = float_screenshots[0]
        float_screenshots.remove(screenshot)
        cord = get_cord(driver,img)
        size_x, size_y = img.size['width'], img.size['height']
        cord_x, cord_y = cord['x'], cord['y']
        if check_img(driver,img):
            src = img.get_attribute('src')
            sheet.write(current_line,0,src)
            sheet.write(current_line,1,f'({size_x}, {size_y}')
            sheet.write(current_line,2,f'({cord_x}, {cord_y})')
            current_line+=1
            img_data = img.screenshot_as_png
            os.mkdir(os.path.join(folder_name,str(current_num)))
            with open(f'{folder_name}/{str(current_num)}/source.png', 'wb') as f:
                f.write(img_data)
            cv2.imwrite(f'{folder_name}/{str(current_num)}/screenshot.png',screenshot)
            current_num+=1
    info_xls.save(f'./{folder_name}/infos.xls')
        
    return current_num

        
def set_args():
    description = 'Following parameter is avaliable:'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--i',help = 'read urls from file, support csv and txt')
    parser.add_argument('--s',help='start index')
    parser.add_argument('--e', help='end index')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = set_args()
    xls_log = xlwt.Workbook(encoding='UTF-8')
    table_log = xls_log.add_sheet('meta_infos',cell_overwrite_ok=True)
    table_log.write(0,0,'URL')
    table_log.write(0,1,'Float Img Count')
    proxy_ip = '127.0.0.1'
    proxy_port = '7890'
    line = 1
    file = args.i
    start_index = int(args.s)
    end_index = args.e
    lenth = int(end_index) - int(start_index)
    assert(lenth > 0)
    file_type = os.path.splitext(file)[-1][1:]
    # 从文本文件读取网址
    window_width = 1920
    window_height = 1080
    if file_type == 'txt':
        with open('urls.txt', 'r') as f:
            urls = f.read().splitlines()[int(start_index):int(end_index)]
    elif file_type == 'csv':
        urls = []
        with open(file) as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                if start_index >0:
                    start_index -=1
                else:
                    urls.append(row[1])
                    if(len(urls)==lenth):
                        break
    else:
        print('Please input a valid filename')
        exit(0)
    dir_name = 'float_img_data_'+time.strftime('%Y_%m_%d_%H_%M_%S',time.localtime())
    if not os.path.exists(f'./{dir_name}'):
        os.mkdir(f'./{dir_name}')
    os.chdir(f'./{dir_name}')
    # 创建Driver
    load_policy = DesiredCapabilities.EDGE
    load_policy["pageLoadStrategy"]='none'
    edge_drive_path = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedgedriver.exe'
    svc = Service('C:/Program Files (x86)/Microsoft/Edge/Application/msedgedriver.exe')
    optn = webdriver.EdgeOptions()
    optn.page_load_strategy = 'none'
    optn.add_argument('--headless')
    optn.add_argument('--ignore-certificate-errors')
    optn.add_argument('--ignore-ssl-errors')

    optn.add_argument(f'--proxy-server=http://{proxy_ip}:{proxy_port}')
    driver = webdriver.Edge(service=svc,options=optn)
    #driver.set_page_load_timeout(20)
    #driver.set_script_timeout(20)

    for url in urls:
        try:
            print(f'[PROGRESS]===> {round((urls.index(url)/len(urls))*100,2)}%   {str(urls.index(url))}/{str(len(urls))}')
            if not url.startswith('//') and not url.startswith('http'):
                url = '//' + url
            url = urlparse.urlunparse(urlparse.urlparse(url,scheme = 'http'))
            driver.get(url)
            time.sleep(15)
            driver.execute_script('window.stop()')
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
            table_log.write(line,0,url)
            table_log.write(line,1,str(float_img_count))
            line+=1
        except Exception as e:
            print(f'ERROR: {e}')
    xls_log.save('log.xls')
    driver.quit()