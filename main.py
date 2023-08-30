import base64
import requests
import xlwt
import time
import os
import binascii

from selenium import webdriver
from PIL import Image
from bs4 import BeautifulSoup

import task

from io import BytesIO
from PIL import Image
import shutil
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

import tkinter

# global counter for <img>
image_id = 0
iframe_id = 1

image_list = []


def script_add_tag_for_all_image():
    script = "var image_id = " + str(image_id) + ";" + '''
            image_elements = document.getElementsByTagName(\"img\");
            for(let i=0;i < image_elements.length; i++) {
                let img = image_elements[i];
                if (!img.classList.contains("tracked_image_by_adpos")) {
                    img.classList.add("tracked_image_by_adpos");
                    img.setAttribute('image-id-adpos', image_id.toString());
                    image_id++;
                }
            }
            return image_id;
        '''
    return script


def script_add_tag_for_iframe():
    script = "var iframe_id = " + str(iframe_id) + ";" + '''
        if (!arguments[0].classList.contains("tracked_iframe_by_adpos")) {
            arguments[0].classList.add('tracked_iframe_by_adpos');
            arguments[0].setAttribute('iframe-id-adpos', iframe_id.toString());
            iframe_id++;
        }
        var now_frame_id = parseInt(arguments[0].getAttribute("iframe-id-adpos"));
        return [iframe_id, now_frame_id];
    '''

    return script


def script_get_element_actual_position():
    script = '''
        // 获取元素的绝对位置坐标（像对于页面左上角）
        function getElementPagePosition(element){
            //计算x坐标
            var actualLeft = element.offsetLeft;
            var current = element.offsetParent;
            while (current !== null){
                actualLeft += current.offsetLeft;
                current = current.offsetParent;
            }
            //计算y坐标
            var actualTop = element.offsetTop;
            var current = element.offsetParent;
            while (current !== null){
                actualTop += (current.offsetTop+current.clientTop);
                current = current.offsetParent;
            }
            //返回结果
            return {x: actualLeft, y: actualTop}
        }
    '''
    return script


def scan_frame_add_tags(driver, frame=None):
    global iframe_id
    global image_id
    global image_list

    driver.switch_to.default_content()
    now_frame_id = 0

    if frame:
        iframe_id, now_frame_id = driver.execute_script(script_add_tag_for_iframe(), frame)
    '''
    if frame:
        if "tracked_iframe_by_adpos" in frame.get_attribute('class'):
            now_frame_id = int(frame.get_attribute("iframe-id-adpos"));
        else:
            driver.execute_script("arguments[0].classList.add('tracked_iframe_by_adpos')", frame)
            driver.execute_script("arguments[0].setAttribute('iframe-id-adpos', " + str(iframe_id) + ")", frame)
            now_frame_id = iframe_id
            iframe_id = iframe_id + 1
    '''

    if frame:
        driver.switch_to.frame(frame)

    pre_img_id = image_id
    now_img_id = driver.execute_script(script_add_tag_for_all_image())
    image_id = now_img_id

    image_list.extend([{'tag': img_id, 'frame': now_frame_id} for img_id in range(pre_img_id, now_img_id)])


def add_tag_for_main_and_iframe(driver):
    driver.switch_to.default_content()
    scan_frame_add_tags(driver)
    iframes = driver.find_elements(By.TAG_NAME, 'iframe')
    for iframe in iframes:
        scan_frame_add_tags(driver, iframe)


def scroll_through_whole_page(driver):
    max_scroll_times = 15
    # 获取页面初始高度
    initial_height = task.get_height(driver)

    scroll_times = 0
    # 模拟滚动操作
    while True:
        scroll_times = scroll_times + 1
        # 执行滚动操作
        driver.execute_script("window.scrollTo(0, " + str(initial_height) + ");")
        # 等待页面加载
        # driver.implicitly_wait(20)
        time.sleep(1)
        # 获取滚动后的高度
        new_height = task.get_height(driver)
        # 判断是否到达页面底部
        if new_height == initial_height:
            break
        # 更新页面初始高度
        initial_height = new_height

        if scroll_times > max_scroll_times:
            break

    return initial_height


def update_information_in_image_list(driver):
    for iframe_tag in range(iframe_id):
        driver.switch_to.default_content()
        driver.save_screenshot("./tmp/tmp.png")

        offset = (0, 0)
        if iframe_tag:
            try:
                iframe = driver.find_element(By.XPATH, "//iframe[@iframe-id-adpos='" + str(iframe_tag) + "']")
                offset = (iframe.location.get('x'), iframe.location.get('y'))
                driver.switch_to.frame(iframe)
            except WebDriverException as e:
                print(f"Failed to switch to frame {iframe_tag}. Reason: {e}")
                continue

        images = driver.execute_script(script_get_element_actual_position() + '''
            let img_elements = document.getElementsByClassName("tracked_image_by_adpos");
            let ret = new Array();
            for(let i=0; i<img_elements.length; i++) {
                let image = img_elements[i];
                let j = {};
                j.tag = parseInt(image.getAttribute("image-id-adpos"));
                j.src = image.getAttribute("src");
                j.size = { width: image.width, height: image.height};
                j.pos = getElementPagePosition(image);
                
                ret.push(j);
            }
            return ret;
            ''')

        full_screenshot = Image.open("./tmp/tmp.png")
        full_screenshot.show()

        for image_ret in images:
            image = image_list[image_ret["tag"]]

            src = image_ret["src"]
            pos = (image_ret["pos"]["x"] + offset[0], image_ret["pos"]["y"] + offset[1])
            size = (image_ret["size"]["width"], image_ret["size"]["height"])

            if "src" in image:
                image["src"].append(src)
            else:
                image["src"] = [src]

            if "pos" in image:
                image["pos"].append(pos)
            else:
                image["pos"] = [pos]

            if "size" in image:
                image["size"].append(size)
            else:
                image["size"] = [size]

            ud_border = max(0.2 * (0.5 * size[1]), 30)
            lr_border = max(0.2 * (0.5 * size[0]), 30)

            element_screenshot = full_screenshot.crop((pos[0] - lr_border,
                                                       pos[1] - ud_border,
                                                       pos[0] + size[0] + lr_border,
                                                       pos[1] + size[1] + ud_border))

            element_screenshot.show()
        '''
        image_in_frame = filter(lambda x: x["frame"] == iframe_tag, image_list)
        for image in image_in_frame:
            try:
                img_element = driver.find_element(By.XPATH, "//img[@image-id-adpos = '" + str(image["tag"]) + "']")
                client_position = driver.execute_script("arguments[0].scrollIntoView({ block: \"center\"});" +
                                            "return arguments[0].getBoundingClientRect();", img_element)
                driver.save_screenshot("temp.png")
            except WebDriverException as e:
                print(f"Failed to get image {image['tag']}. Reason: {e}")
                continue

            if img_element:
                src = None
                try:
                    src = img_element.get_attribute('src')
                except WebDriverException as e:
                    print(f"Failed to get src attribute for {img_element}. Reason: {e}")

                pos_in_frame = (img_element.location.get('x'), img_element.location.get('y'))
                pos = pos_in_frame + offset
                size = img_element.size.values()

                full_screenshot = Image.open("temp.png")

                ud_border = max(0.2*(0.5*client_position["height"]), 30)
                lr_border = max(0.2*(0.5*client_position["width"]), 30)
                element_screenshot = full_screenshot.crop((client_position["left"] - lr_border,
                                                           client_position["top"] - ud_border,
                                                           client_position["right"] + lr_border,
                                                           client_position["bottom"] + ud_border))
                element_screenshot.show()

                if "src" in image:
                    image["src"].append(src)
                else:
                    image["src"] = [src]

                if "pos" in image:
                    image["pos"].append(pos)
                else:
                    image["pos"] = [pos]

                if "size" in image:
                    image["size"].append(size)
                else:
                    image["size"] = [size]
        '''


if __name__ == "__main__":
    with open('./resource/urls.txt', 'r', encoding='utf8') as f:
        urls = f.readlines()

    screen = tkinter.Tk()

    # 创建驱动
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--window-size=' + str(screen.winfo_screenwidth()) +
                                'x' + str(screen.winfo_screenheight()))
    driver = webdriver.Chrome(options=chrome_options)

    m = 0
    times = 0
    for url in urls:
        times = times+1
        # print("This is " + url)

        pic = xlwt.Workbook(encoding='utf-8', style_compression=0)
        sheet = pic.add_sheet('广告收集', cell_overwrite_ok=True)
        sheet.write(0, 0, 'src')
        sheet.write(0, 1, 'pos_x')
        sheet.write(0, 2, 'pos_y')
        sheet.write(0, 3, 'size_x')
        sheet.write(0, 4, 'size_y')
        sheet.write(0, 5, '广告种类')
        sheet.write(0, 6, '亮度')
        sheet.write(0, 7, '饱和度')
        sheet.write(0, 8, '来源')
        sheet.write(0, 9, '图片总量')
        sheet.write(0, 10, '页面总面积')
        sheet.write(0, 11, '文字')
        sheet.write(0, 12, "minmax")
        sheet.write(0, 18, "颜色种类数")
        sheet.write(0, 19, "最大颜色数量占据的比例")
        sheet.write(0, 20, "最大颜色RGB值")

        n = 1
        m = m + 1
        try:
            driver.get(url)

            whole_page_height = scroll_through_whole_page(driver)
            whole_page_width = task.get_width(driver)

            # 获取页面总面积
            total_area = whole_page_width * whole_page_height

            # 设置浏览器大小为全页面大小，仅限headless模式下可用
            driver.set_window_size(whole_page_width, whole_page_height)

        except Exception as e:
            print("driver get error")

        # driver.implicitly_wait(50)
        time.sleep(5)

        add_tag_for_main_and_iframe(driver)

        update_information_in_image_list(driver)

    driver.close()
