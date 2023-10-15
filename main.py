import base64

import PIL
import requests
import time
import pandas as pd
import re
import os
import io
import sys
import imghdr
import binascii
import getopt
import urllib.parse as urlparse
import urllib3.exceptions as urlexceptions

import task
from PIL import Image
import cairosvg
import shutil
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

import tkinter

# global counter for <img> and <iframe>
image_id = 0
iframe_id = 1

image_list = []


def script_import_domtoimage():
    script = '''
        var script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = 'http://localhost:8080/dom-to-image.js';
        document.body.appendChild(script);
    '''

    return script


def script_import_fireshot():
    script = '''
        var script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = 'http://localhost:8080/fsapi.js';
        document.body.appendChild(script);
    '''

    return script


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
        if(typeof(getElementPagePosition) === 'undefined') {
            function getElementPagePosition(element) {
                Rect = element.getBoundingClientRect();
                x = Rect.left;
                y = Rect.top;
                return {x: x, y: y};
            }
        }
    '''

    '''
        if(typeof(getElementPagePosition) === 'undefined') {
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
        }
    '''
    return script


def script_register_log_and_set_observer():
    script = script_get_element_actual_position() + '''
        if(typeof(intersection_log) === 'undefined')
            intersection_log = [];

        const intersectionOb = new IntersectionObserver(entries => {
            for(const entry of entries) {
                let j = {};
                
                let image = entry.target;
                j.tag = parseInt(image.getAttribute("image-id-adpos"));
                j.src = image.getAttribute("src");
                j.size = { width: image.width, height: image.height};
                j.pos = getElementPagePosition(image);

                if(j.isIntersecting() && j.size.width > 0 && j.size.height > 0 && j.pos.x > 0 && j.pos.y >0) {
                    
                    intersection_log.push(j);
                }
            }
        });

        let img_elements = document.getElementsByClassName("tracked_image_by_adpos");
        for(let i=0; i<img_elements.length; i++) {
            let image = img_elements[i];
            let current = image.offsetParent;
            while (current !== null) {
                if(current.nodeName == "BODY") {
                    intersectionOb.observe(image, { root: current });
                    break;
                }
                current = current.offsetParent;
            }
        }
        '''

    return script


def script_register_log_and_set_interval():
    script = script_get_element_actual_position() + '''
        if(typeof(log_dic) === 'undefined')
            log_dic = {}
            
        setInterval(function() {
            let img_elements = document.getElementsByClassName("tracked_image_by_adpos");
            for(let i=0; i<img_elements.length; i++) {
                let image = img_elements[i];
                let j = {};
                
                j.tag = parseInt(image.getAttribute("image-id-adpos"));
                j.src = image.getAttribute("src");
                j.size = {width: image.width, height: image.height};
                j.pos = getElementPagePosition(image);
                
                if(j.size.width > 0 && j.size.height > 0) {
                    if(!log_dic.hasOwnProperty(j.tag))
                        log_dic[j.tag] = new Array();
                    let in_dic = false;
                    for(const bef of log_dic[j.tag]) {
                        if (j.src === bef.src && j.pos.x === bef.pos.x && j.pos.y === bef.pos.y && 
                        j.size.width === bef.size.width && j.size.height === bef.size.height) {
                            in_dic = true;
                            break;
                        }
                    }
                    if(!in_dic) {
                        FireShotAPI.savePage(true, undefined, "D:/ad_position/Web/tmp/cxk.png");
                    }
                }
            }
        }, 1000);
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
        driver.switch_to.frame(frame)

    pre_img_id = image_id
    now_img_id = driver.execute_script(script_add_tag_for_all_image())
    image_id = now_img_id

    image_list.extend([{'tag': img_id, 'frame': now_frame_id, 'info': []} for img_id in range(pre_img_id, now_img_id)])


def add_tag_for_main_and_iframe(driver):
    driver.switch_to.default_content()
    scan_frame_add_tags(driver)
    iframes = driver.find_elements(By.TAG_NAME, 'iframe')
    for iframe in iframes:
        scan_frame_add_tags(driver, iframe)


def scroll_through_whole_page(driver):
    max_scroll_times = 3
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


def update_information_in_image_list(driver, screen_width, screen_height):
    for iframe_tag in range(iframe_id):
        driver.switch_to.default_content()

        offset = (0, 0)
        if iframe_tag:
            try:
                iframe = driver.find_element(By.XPATH, "//iframe[@iframe-id-adpos='" + str(iframe_tag) + "']")
                offset = (iframe.location.get('x'), iframe.location.get('y'))
                driver.switch_to.frame(iframe)
            except WebDriverException as e:
                print(f"Failed to switch to frame {iframe_tag}. Reason: {e}")
                continue

        driver.save_screenshot("./tmp/tmp.png")
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
            '''
        )

        full_screenshot = Image.open("./tmp/tmp.png")
        # full_screenshot.show()

        for image_ret in images:
            image = image_list[image_ret["tag"]]

            src = image_ret["src"]
            pos = (image_ret["pos"]["x"] + offset[0], image_ret["pos"]["y"] + offset[1])
            size = (image_ret["size"]["width"], image_ret["size"]["height"])

            image_info = dict()

            image_info["src"] = src
            image_info["size"] = size
            image_info["pos"] = pos
            image_info["inner_id"] = len(image["info"])

            image["info"].append(image_info)

            ud_border = max(0.2 * (0.5 * size[1]), 30)
            lr_border = max(0.2 * (0.5 * size[0]), 30)

            element_screenshot = full_screenshot.crop((pos[0] - lr_border,
                                                       pos[1] - ud_border,
                                                       pos[0] + size[0] + lr_border,
                                                       pos[1] + size[1] + ud_border))

            # element_screenshot.show()
            element_screenshot.save("./tmp/" + str(image["tag"]) + "_" + str(image_info["inner_id"]) + ".png")

            bigger_screenshot = full_screenshot.crop((pos[0] - screen_width / 2,
                                                      pos[1] - screen_height / 2,
                                                      pos[0] + size[0] + screen_width / 2,
                                                      pos[1] + size[1] + screen_height / 2))
            # bigger_screenshot.show()
            bigger_screenshot.save("./tmp/" + str(image["tag"]) + "_" + str(image_info["inner_id"]) + "_big.png")


def set_interval_in_main_and_iframe(driver):
    for iframe_tag in range(iframe_id):
        driver.switch_to.default_content()
        if iframe_tag:
            try:
                iframe = driver.find_element(By.XPATH, "//iframe[@iframe-id-adpos='" + str(iframe_tag) + "']")
                driver.switch_to.frame(iframe)
            except WebDriverException as e:
                print(f"Failed to switch to frame {iframe_tag}. Reason: {e}")
                continue

        driver.execute_script(script_register_log_and_set_interval())

    return


def import_domtoimage_in_main_and_iframe(driver):
    for iframe_tag in range(iframe_id):
        driver.switch_to.default_content()
        if iframe_tag:
            try:
                iframe = driver.find_element(By.XPATH, "//iframe[@iframe-id-adpos='" + str(iframe_tag) + "']")
                driver.switch_to.frame(iframe)
            except WebDriverException as e:
                print(f"Failed to switch to frame {iframe_tag}. Reason: {e}")
                continue

        driver.execute_script(script_import_domtoimage())
    return


def import_fireshot_in_main_and_iframe(driver):
    for iframe_tag in range(iframe_id):
        driver.switch_to.default_content()
        if iframe_tag:
            try:
                iframe = driver.find_element(By.XPATH, "//iframe[@iframe-id-adpos='" + str(iframe_tag) + "']")
                driver.switch_to.frame(iframe)
            except WebDriverException as e:
                print(f"Failed to switch to frame {iframe_tag}. Reason: {e}")
                continue

        driver.execute_script(script_import_fireshot())
    return


def not_in_list(infos, src, size, pos):
    for info in infos:
        if info["src"] == src and info["size"] == size and info["pos"] == pos:
            return False

    return True


def track_imgs_in_image_list(driver, screen_width, screen_height):
    for image in image_list:
        driver.switch_to.default_content()
        offset = (0, 0)

        iframe_tag = image["frame"]
        if iframe_tag:
            try:
                iframe = driver.find_element(By.XPATH, "//iframe[@iframe-id-adpos='" + str(iframe_tag) + "']")
                offset = (iframe.location.get('x'), iframe.location.get('y'))
                driver.switch_to.frame(iframe)
            except WebDriverException as e:
                print(f"Failed to switch to frame {iframe_tag}. Reason: {e}")
                continue

        print(">>>>Tracking image: %d/%d" % (image["tag"], len(image_list)))

        max_size = 6
        max_time, once_time, timer = 4000, 1000, 0
        while len(image["info"]) <= max_size:
            driver.save_screenshot("./tmp/tmp.png")

            info = driver.execute_script(script_get_element_actual_position() + '''
                let image = document.querySelector("img[image-id-adpos='%s']");
                
                let j = {src: null, size: null, pos: null};
                if(image) {
                    j.src = image.getAttribute("src");
                    j.size = { width: image.width, height: image.height};
                    j.pos = getElementPagePosition(image);
                }
                return j;
                ''' % (str(image["tag"]))
            )

            if info["pos"] and info["size"]:
                src = info["src"]
                pos = (info["pos"]["x"] + offset[0], info["pos"]["y"] + offset[1])
                size = (info["size"]["width"], info["size"]["height"])
                inner_id = len(image["info"])

                if not_in_list(image["info"], src, size, pos):
                    image_info = {'src': src, 'pos': pos, 'size': size, 'inner_id': inner_id}

                    image["info"].append(image_info)
                    timer = 0

                    screenshot = Image.open("./tmp/tmp.png")
                    # screenshot.show()

                    ud_border = max(0.2 * (0.5 * size[1]), 30)
                    lr_border = max(0.2 * (0.5 * size[0]), 30)

                    element_screenshot = screenshot.crop((pos[0] - lr_border,
                                                          pos[1] - ud_border,
                                                          pos[0] + size[0] + lr_border,
                                                          pos[1] + size[1] + ud_border))
                    # element_screenshot.show()
                    element_screenshot.save("./tmp/" + str(image["tag"]) + "_" + str(image_info["inner_id"]) + ".png")

                    bigger_screenshot = screenshot.crop((pos[0] - screen_width / 2,
                                                         pos[1] - screen_height / 2,
                                                         pos[0] + size[0] + screen_width / 2,
                                                         pos[1] + size[1] + screen_height / 2))
                    # bigger_screenshot.show()
                    bigger_screenshot.save("./tmp/" + str(image["tag"]) + "_" + str(image_info["inner_id"]) + "_big.png")

            time.sleep(once_time/1000.0)
            timer = timer + once_time
            if timer >= max_time:
                break


def transform_infos_to_dataframe(infos):
    p = pd.json_normalize(data=infos)

    return p


def info_check_valid(info):
    if info["src"] and info["size"][0] > 0 and info["size"][1] > 0:
        return True
    return False


def image_check_valid(infos):
    for info in infos:
        if info_check_valid(info):
            return True

    return False


def extract_from_url(image_url):
    if "data:image" in image_url:
        if "/jpeg" in image_url:
            return "jpg"
        if "/png" in image_url:
            return "png"
        if "/gif" in image_url:
            return "gif"
        if "/svg+xml" in image_url:
            return "svg"

    if ".svg" in image_url:
        return "svg"
    if ".jpeg" in image_url or ".jpg" in image_url:
        return "jpg"
    if ".png" in image_url:
        return "png"
    if ".webp" in image_url:
        return "webp"

    return "jpg"


def write_to_file(output_dir, url, height, width):
    print("Write information...")
    dir_name = os.path.join(output_dir, re.sub(r'[\\/:*?"<>|]', '_', url))

    if os.path.exists(dir_name):
        shutil.rmtree(dir_name)

    os.makedirs(dir_name)

    id_image = 0
    for image in image_list:
        image_dir_name = os.path.join(dir_name, str(id_image))
        os.makedirs(image_dir_name)

        infos = []
        id_info = 0

        for info in image["info"]:
            if info_check_valid(info):
                url_modified = ""
                try:
                    url_modified = urlparse.urlunparse(urlparse.urlparse(urlparse.urljoin(driver.current_url, info["src"]), scheme="http"))
                    content = requests.get(url_modified).content
                except urlexceptions.LocationParseError as e:
                    print(f'Urllib Error: {e}')
                    continue
                except requests.exceptions.HTTPError as e:
                    print(f'HTTP Error: {e}')
                    continue
                except requests.exceptions.RequestException as e:
                    if "data:image/" in info["src"]:
                        src_encode = info["src"].split(',')[-1]
                        if ";base64" in info["src"]:
                            try:
                                content = base64.b64decode(src_encode)
                            except binascii.Error as err:
                                print(f'Decode Error: {err}')
                                continue
                        else:
                            content = bytes(urlparse.unquote(src_encode).encode())
                    else:
                        print(f'Request Error: {e}')
                        continue

                image_type = imghdr.what(None, h=content) or extract_from_url(url_modified)

                info_dir_name = os.path.join(image_dir_name, str(id_info))
                os.makedirs(info_dir_name)

                screenshot_filepath = "./tmp/" + str(image["tag"]) + "_" + str(info["inner_id"]) + ".png"
                shutil.move(screenshot_filepath, info_dir_name + "/screenshot.png")

                big_screenshot_filepath = "./tmp/" + str(image["tag"]) + "_" + str(info["inner_id"]) + "_big.png"
                shutil.move(big_screenshot_filepath, info_dir_name + "/bigshot.png")

                if image_type == "svg":
                    try:
                        content = cairosvg.svg2png(bytestring=content)
                    except Exception as e:
                        print(f'Failed to translate svg to png, {e}')
                        shutil.rmtree(info_dir_name)
                        continue
                    image_type = "png"

                try:
                    Image.open(io.BytesIO(content)).save(info_dir_name + "/source." + image_type)
                except Exception as e:
                    print(f'Can not open file: {url_modified} as an image.')
                    shutil.rmtree(info_dir_name)
                    continue

                info_output = info.copy()
                info_output["inner_id"] = id_info
                infos.append(info_output)

                id_info = id_info + 1

        infos_file = pd.ExcelWriter(image_dir_name + "/infos.xlsx")
        transform_infos_to_dataframe(infos).assign(valid="", advertisement="").to_excel(infos_file, index=False)
        infos_file.close()

        if id_info:
           id_image = id_image + 1
        else:
            shutil.rmtree(image_dir_name)

    metadata = {'width': width, 'height': height}
    pf = pd.json_normalize(data=metadata)
    pf['type'] = None
    meta_file = pd.ExcelWriter(dir_name + "/meta.xlsx")
    pf.to_excel(meta_file, index=True)
    meta_file.close()

    print('Done')


if __name__ == "__main__":
    output_dir = None
    input_path = None
    fromto = None
    opts, args = getopt.getopt(sys.argv[1:], 'o:i:', longopts=['index='])
    for opt_name, opt_value in opts:
        if opt_name == '-o':
            output_dir = opt_value
        if opt_name == '-i':
            input_path = opt_value
        if opt_name == '--index':
            fromto = opt_value

    url_df = pd.read_csv(input_path, header=None)
    urls = url_df.iloc[:, 1].values.tolist()

    index_begin, index_end = 0, len(urls)

    if fromto:
        split = fromto.split(',')
        user_begin = split[0] if len(split[0]) else "0"
        user_end = split[1] if len(split[1]) else "2100000000"
        index_begin = max(index_begin, int(user_begin))
        index_end = min(index_end, int(user_end) + 1)

    # screen = tkinter.Tk()
    # screen_width, screen_height = screen.winfo_screenwidth(), screen.winfo_screenheight()
    screen_width, screen_height = 1920, 1080

    # 创建驱动
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--window-size=' + str(screen_width) + 'x' + str(screen_height))

    for url in urls[index_begin:index_end]:
        image_id = 0
        iframe_id = 1
        image_list = []

        driver = webdriver.Chrome(options=chrome_options)

        if not url.startswith("//"):
            url = "//" + url
        url_reg = urlparse.urlunparse(urlparse.urlparse(url, scheme="http"))
        print(">>Tracking url: " + url_reg)

        try:
            driver.get(url_reg)

            time.sleep(5)

            whole_page_height = scroll_through_whole_page(driver)
            whole_page_width = task.get_width(driver)

            # 设置浏览器大小为全页面大小，仅限headless模式下可用
            driver.set_window_size(whole_page_width, whole_page_height)

        except Exception as e:
            print(f"driver get error {e}")
            continue

        # driver.implicitly_wait(50)
        time.sleep(30)

        add_tag_for_main_and_iframe(driver)

        # import_domtoimage_in_main_and_iframe(driver)
        # import_fireshot_in_main_and_iframe(driver)

        update_information_in_image_list(driver, screen_width, screen_height)

        # set_interval_in_main_and_iframe(driver)

        # time.sleep(3)

        track_imgs_in_image_list(driver, screen_width, screen_height)

        write_to_file(output_dir, url_reg, whole_page_height, whole_page_width)

        driver.quit()