import os
import pandas as pd
from cnocr import CnOcr
import getopt
import sys
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')


if __name__ == "__main__":
    input_dir = None
    opts, args = getopt.getopt(sys.argv[1:], 'i:')
    for opt_name, opt_value in opts:
        if opt_name == '-i':
            input_dir = opt_value

    ocr = CnOcr(rec_model_name='ch_PP-OCRv3')  # 所有参数都使用默认值

    dir_path = input_dir
    url_dirs = os.listdir(dir_path)
    for file in url_dirs:
        url_dir_path = os.path.join(dir_path, file)
        if os.path.isdir(url_dir_path):
            advertisements = []
            normal_images = []

            image_dirs = os.listdir(url_dir_path)
            for image_dir in image_dirs:
                image_dir_path = os.path.join(url_dir_path, image_dir)
                if os.path.isdir(image_dir_path):
                    df = pd.read_excel(os.path.join(image_dir_path, "infos.xlsx"))
                    df_valid = df.loc[df['valid'] == 1]
                    if df_valid.shape[0]:
                        src = df_valid['src'].iloc[0]
                        size = eval(df_valid['size'].iloc[0])
                        pos = eval(df_valid['pos'].iloc[0])

                        for info_name in os.listdir(os.path.join(image_dir_path, df_valid['inner_id'].iloc[0].astype(str))):
                            if os.path.splitext(info_name)[0] == "source":
                                ocr_output = ocr.ocr(os.path.join(image_dir_path, df_valid['inner_id'].iloc[0].astype(str), info_name))

                        txt = ""
                        for item in ocr_output:
                            if item['score'] >= 0.5:
                                txt += item["text"].strip() + '###'

                        if df_valid['advertisement'].iloc[0]:
                            advertisements.append({'src': src, 'pos': pos, 'size': size, 'txt': txt})
                        else:
                            normal_images.append({'src': src, 'pos': pos, 'size': size, 'txt': txt})
                else:
                    if image_dir == "meta.xlsx":
                        df = pd.read_excel(os.path.join(image_dir_path))
                        whole_page_width = df['width'].iloc[0]
                        whole_page_height = df['height'].iloc[0]

            total_images_count = len(advertisements) + len(normal_images)
            total_advertisements_count = len(advertisements)

            whole_page_area = whole_page_width * whole_page_height
            normal_area = 0
            ad_area = 0
            for nor in normal_images:
                normal_area = normal_area + nor["size"][0] * nor["size"][1]

            for ad in advertisements:
                ad_area = ad_area + ad["size"][0] * ad["size"][1]

            ad_pr = pd.DataFrame(columns=["pos_x", "pos_y", "rel_pos_x", "rel_pos_y", "size_x", "size_y", "rel_size_x", "rel_size_y"])
            ad_pr['pos_x'] = [x['pos'][0] for x in advertisements]
            ad_pr['pos_y'] = [x['pos'][1] for x in advertisements]
            ad_pr['rel_pos_x'] = [x['pos'][0] / whole_page_width for x in advertisements]
            ad_pr['rel_pos_y'] = [x['pos'][1] / whole_page_height for x in advertisements]
            ad_pr['size_x'] = [x['size'][0] for x in advertisements]
            ad_pr['size_y'] = [x['size'][1] for x in advertisements]
            ad_pr['rel_size_x'] = [x['size'][0] / whole_page_width for x in advertisements]
            ad_pr['rel_size_y'] = [x['size'][1] / whole_page_height for x in advertisements]

            nor_pr = pd.DataFrame(columns=["pos_x", "pos_y", "rel_pos_x", "rel_pos_y", "size_x", "size_y", "rel_size_x", "rel_size_y"])
            nor_pr['pos_x'] = [x['pos'][0] for x in normal_images]
            nor_pr['pos_y'] = [x['pos'][1] for x in normal_images]
            nor_pr['rel_pos_x'] = [x['pos'][0] / whole_page_width for x in normal_images]
            nor_pr['rel_pos_y'] = [x['pos'][1] / whole_page_height for x in normal_images]
            nor_pr['size_x'] = [x['size'][0] for x in normal_images]
            nor_pr['size_y'] = [x['size'][1] for x in normal_images]
            nor_pr['rel_size_x'] = [x['size'][0] / whole_page_width for x in normal_images]
            nor_pr['rel_size_y'] = [x['size'][1] / whole_page_height for x in normal_images]

            # rel_pos

            fig = plt.figure(figsize=(16, 16))
            ax1 = fig.add_subplot(221)
            ax2 = fig.add_subplot(222)

            ad_pr.plot.scatter(x='rel_pos_x', y='rel_pos_y', color='b', label='ad', marker='.', ax=ax1)
            nor_pr.plot.scatter(x='rel_pos_x', y='rel_pos_y', color='r', label='not ad', marker='x', ax=ax2)
            plt.show()

            # rel_pos_x

            plt.style.use('ggplot')
            # 处理中文乱码
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
            # 坐标轴负号的处理
            plt.rcParams['axes.unicode_minus'] = False
            # 绘制直方图
            sns.distplot(ad_pr["rel_pos_x"], bins=20, kde=False, hist_kws={'color': 'yellow'}, label='ad')
            sns.distplot(nor_pr["rel_pos_x"], bins=20, kde=False, hist_kws={'color': 'steelblue'}, label='not ad')

            plt.xlabel('pos_x')
            plt.ylabel('频数')
            # 添加标题
            plt.title('pos_x of the all type')
            # 显示图例
            plt.legend()
            # 显示图形
            plt.show()

            # rel_pos_y

            plt.style.use('ggplot')
            # 处理中文乱码
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
            # 坐标轴负号的处理
            plt.rcParams['axes.unicode_minus'] = False
            # 绘制直方图
            sns.distplot(ad_pr["rel_pos_y"], bins=20, kde=False, hist_kws={'color': 'yellow'}, label='ad')
            sns.distplot(nor_pr["rel_pos_y"], bins=20, kde=False, hist_kws={'color': 'steelblue'}, label='not ad')

            plt.xlabel('pos_y')
            plt.ylabel('频数')
            # 添加标题
            plt.title('pos_y of the all type')
            # 显示图例
            plt.legend()
            # 显示图形
            plt.show()
