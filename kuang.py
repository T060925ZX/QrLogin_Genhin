import tkinter as tk
import ctypes

# 扫描窗口配置（与main.py保持一致）
WIN_WIDTH = 300
WIN_HEIGHT = 300

# DPI适配
def get_dpi_scale():
    """获取屏幕DPI缩放比例"""
    try:
        root = tk.Tk()
        root.withdraw()
        dpi_x = root.winfo_fpixels('1i')
        root.destroy()
        return round(dpi_x / 96.0, 2)
    except:
        try:
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
            ctypes.windll.user32.ReleaseDC(0, hdc)
            return round(dpi / 96.0, 2)
        except:
            return 1.0

# 获取DPI缩放比例
DPI_SCALE = get_dpi_scale()
PHYSICAL_WIDTH = int(WIN_WIDTH * DPI_SCALE)
PHYSICAL_HEIGHT = int(WIN_HEIGHT * DPI_SCALE)

# 创建一个Tkinter窗口
root = tk.Tk()

# 隐藏窗口标题栏和边框
root.overrideredirect(True)

# 将窗口置顶
root.wm_attributes("-topmost", True)

# 设置窗口大小和位置（使用物理像素）
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x_pos = (screen_width // 2) - (PHYSICAL_WIDTH // 2)
y_pos = (screen_height // 2) - (PHYSICAL_HEIGHT // 2)
root.geometry('{}x{}+{}+{}'.format(PHYSICAL_WIDTH, PHYSICAL_HEIGHT, x_pos, y_pos))

# 将窗口背景设为透明
root.attributes('-transparentcolor', 'white')

# 将窗口的画布设为透明
canvas = tk.Canvas(root, bg='white', highlightthickness=0)
canvas.pack(fill='both', expand=True)

# 绘制红色空心正方形（边框内缩5像素，按DPI缩放）
border_offset = int(5 * DPI_SCALE)
canvas.create_rectangle(
    border_offset, border_offset, 
    PHYSICAL_WIDTH - border_offset, PHYSICAL_HEIGHT - border_offset, 
    outline='red', width=int(2 * DPI_SCALE)
)

# 进入循环让窗口保持打开状态
root.mainloop()