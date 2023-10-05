import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import Scrollbar
from tkinter import filedialog
from PIL import Image, ImageTk
import os
import openpyxl
from main import template_match


# 全局变量
total_folder_num = 0
current_main_folder_index = 0
current_sub_folder_index = 0
info_file_path = ""
screenshot_images = []
source_images = []
main_folder_path = ""
sub_folders = []
source_label = None 


def open_folder():
    global main_folder_path,total_folder_num
    folder_path = filedialog.askdirectory()  # 打开文件夹选择对话框
    if folder_path:
        main_folder_path = folder_path
        main_folders = [f for f in os.listdir(main_folder_path) if os.path.isdir(os.path.join(main_folder_path, f))]
        total_folder_num = len(os.listdir(main_folder_path))
        print(os.listdir(main_folder_path))
        print(total_folder_num)
        total_folder_num-=1
        load_images()


def openpic(path):
    os.system('start '+path)

def load_images():
    global current_main_folder_index, current_sub_folder_index, info_file_path, screenshot_images, main_folder_path, sub_folders, source_label

    main_folder_name = str(current_main_folder_index)

    sub_folders = [f for f in os.listdir(os.path.join(main_folder_path, main_folder_name)) if os.path.isdir(os.path.join(main_folder_path, main_folder_name, f))]
    ttk.Label()

    offset = []
    index = []
    for idx in range(len(sub_folders)):
        pth = os.path.join(main_folder_path,main_folder_name,str(idx))
        files = os.listdir(pth)
        screenshot = ''
        source = ''
        for f in files:
            if f[:6]=='source':
                source = f
            elif f[:10] == 'screenshot':
                screenshot = f
        match,oset = template_match(os.path.join(pth,screenshot),os.path.join(pth,source))
        if match:
            offset.append(oset)
            index.append(idx)

    best_optn = index[offset.index(min(offset))] if len(offset)!=0 else None
    print(offset)
    print(best_optn)

    if current_sub_folder_index < len(sub_folders):
        sub_folder_name = sub_folders[current_sub_folder_index]

        # 拼接当前子文件夹路径
        current_folder_path = os.path.join(main_folder_path, main_folder_name, sub_folder_name)
    
        # 拼接infos.xlsx文件路径
        info_file_path = os.path.join(main_folder_path, main_folder_name, "infos.xlsx")

        # 打开infos.xlsx
        wb = openpyxl.load_workbook(info_file_path)
        ws = wb.active

        global source_img
        screenshot_images = []

        # 获取当前子文件夹内的所有screenshot.png
        for i in range(len(sub_folders)):
            source_image_path = ""
            fnames = os.listdir(os.path.join(main_folder_path,main_folder_name,sub_folders[i]))
            for f in fnames:
                if f[:6] == "source":
                    source_image_path = os.path.join(current_folder_path, f)
                    break
            screenshot_image_path = os.path.join(main_folder_path, main_folder_name, sub_folders[i], "screenshot.png")
            screenshot_img = Image.open(screenshot_image_path)
            screenshot_img.thumbnail((200, 200))
            screenshot_img = ImageTk.PhotoImage(screenshot_img)
            screenshot_images.append(screenshot_img)  # 将 screenshot 图片添加到列表

            source_img = Image.open(source_image_path)
            source_img.thumbnail((200,200))
            source_img = ImageTk.PhotoImage(source_img)
            source_images.append(source_img)

            # 创建标签和复选框
            screenshot_label = ttk.Label(checkboxes_frame, image=screenshot_img)
            source_label = ttk.Label(checkboxes_frame,image=source_img)
            valid_checkbox = ttk.Checkbutton(checkboxes_frame, text="Valid")
            ad_checkbox = ttk.Checkbutton(checkboxes_frame, text="Ad")
            open_full_button = ttk.Button(checkboxes_frame,text='打开大图',command= lambda:openpic(os.path.join(current_folder_path,'bigshot.png')))
            # 初始化复选框
            valid_checkbox.state(['!alternate'])
            ad_checkbox.state(['!alternate'])

            # 显示图片和复选框
            source_label.grid(row=i,column=1,padx=5,pady=5)
            screenshot_label.grid(row=i, column=0, padx=5, pady=5)
            valid_checkbox.grid(row=i, column=2, padx=5, pady=5)
            ad_checkbox.grid(row=i, column=3, padx=5, pady=5)
            open_full_button.grid(row=i,column=4,padx=5,pady=5)


            if i == best_optn:
                valid_checkbox.state(['selected'])
            # 从infos.xlsx读取并设置复选框状态
            valid_value = ws.cell(row=i+2, column=5).value
            ad_value = ws.cell(row=i+2, column=6).value
            if valid_value == 1:
                valid_checkbox.state(['selected'])
            if ad_value == 1:
                ad_checkbox.state(['selected'])

        # 释放infos.xlsx文件
        wb.close()

def save_changes():
    global total_folder_num,current_main_folder_index
    global info_file_path
    if not info_file_path:
        return

    wb = openpyxl.load_workbook(info_file_path)
    ws = wb.active

    # 更新infos.xlsx中的数据
    row1 = 1
    row2 = 1
    for i, widget in enumerate(checkboxes_frame.winfo_children()):
        if isinstance(widget, ttk.Checkbutton):
            col = 5
            if widget.cget("text") == "Ad":
                col = 6
                row2 += 1
                value = 1 if widget.instate(["selected"]) else 0
                ws.cell(row=row2, column=col, value=value)
            elif widget.cget("text") == "Valid":
                row1 += 1
                value = 1 if widget.instate(["selected"]) else 0
                ws.cell(row=row1, column=col, value=value)


    wb.save(info_file_path)
    wb.close()

    # 清除旧内容
    for widget in checkboxes_frame.winfo_children():
        widget.destroy()
    source_img.__del__()
    if current_main_folder_index == total_folder_num-1:
        tk.messagebox.showinfo(title='提示',message='已完成最后一个文件组的处理！')
        return
    current_main_folder_index+=1
    load_images()
    update_scrollregion()

def show_full():
    global current_main_folder_index
    global main_folder_name
    current_folder_path = os.path.join(main_folder_path, str(current_main_folder_index))
    full_img_name = ''
    path000 = os.path.join(current_folder_path,full_img_name)
    os.system('start '+path000)

def back():
    global current_main_folder_index
    if current_main_folder_index==0:
        tk.messagebox.showinfo(title='提示',message='当前已是第一个图片组')
        return
    current_main_folder_index-=1
    print(current_main_folder_index)
    # 清除旧内容
    for widget in checkboxes_frame.winfo_children():
        widget.destroy()
    source_img.__del__()
    load_images()
    update_scrollregion()

def on_mousewheel(event):
    if event.delta > 0:
        canvas.yview_scroll(-2, "units")  # 向上滚动
    elif event.delta < 0:
        canvas.yview_scroll(2, "units")  # 向下滚动

def update_scrollregion():
    window_width,window_height=root.winfo_width(),root.winfo_height()
    canvas.update_idletasks()  # 更新canvas
    root.geometry(str(window_width)+'x'+str(window_height+1))
    root.geometry(str(window_width)+'x'+str(window_height))
    canvas.yview_scroll(-1000,'units')
    canvas.config(scrollregion=canvas.bbox("all"))  # 重新设置滚动区域

if __name__ == '__main__':

    root = tk.Tk()
    root.title("img tagger")
    root.geometry('800x1000')

    main_folder_path = ""
    main_folders = []

    source_label = ttk.Label(root)
    source_label.pack(padx=20, pady=20)

    canvas = tk.Canvas(root)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    canvas.configure(yscrollcommand=scrollbar.set)

    checkboxes_frame = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=checkboxes_frame, anchor=tk.NW)

    open_folder_button = ttk.Button(root, text="打开文件夹", command=open_folder)
    open_folder_button.pack(padx=20, pady=5)

    show_full_screenshot = ttk.Button(root,text = '打开完整屏幕截图',command = show_full)
    show_full_screenshot.pack(padx=20, pady=5)

    save_button = ttk.Button(root, text="保存修改", command=save_changes)
    save_button.pack(padx=20, pady=5)

    back_button = ttk.Button(root,text='上个图片组',command=back)
    back_button.pack(padx=20, pady=5)

    root.bind("<Return>", lambda event=None: save_changes())
    root.bind("<BackSpace>",lambda event = None: back())
    root.bind("<MouseWheel>", on_mousewheel)
    canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    root.mainloop()
