import cv2
from pyzbar.pyzbar import decode
import pyzbar.pyzbar as pyzbar
import numpy as np
from PIL import ImageGrab
import time
import tkinter as tk
import threading
import re
import http.client
import json
import sys
import ctypes

# ==================== DPI适配 ====================
# 设置DPI感知，避免Windows缩放导致的坐标偏移
try:
    # Windows 10 Anniversary Update 及更高版本
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except:
    try:
        # Windows 8.1 及更早版本
        ctypes.windll.user32.SetProcessDPIAware()  # 系统DPI感知
    except:
        pass  # 无法设置DPI感知，继续使用默认值

def get_dpi_scale():
    """
    获取屏幕DPI缩放比例
    :return: 缩放比例 (例如: 1.0=100%, 1.25=125%, 1.5=150%)
    """
    try:
        # 方法1: 使用tkinter获取
        root = tk.Tk()
        root.withdraw()
        dpi_x = root.winfo_fpixels('1i')  # 每英寸的像素数
        root.destroy()
        scale = dpi_x / 96.0  # 标准DPI是96
        return round(scale, 2)
    except:
        # 方法2: 使用Windows API
        try:
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)
            return round(dpi / 96.0, 2)
        except:
            return 1.0  # 默认无缩放

# ==================== 配置区域 ====================
# 从 stoken.txt 读取 cookie
def load_stoken():
    """从stoken.txt文件读取cookie"""
    try:
        with open('stoken.txt', 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                # 提取stuid
                import re
                match = re.search(r'stuid=(\d+)', content)
                if match:
                    uid = match.group(1)
                    return uid, content
                else:
                    print("⚠ stoken.txt格式错误，未找到stuid")
                    return '0000000', ''
            else:
                print("⚠ stoken.txt为空")
                return '0000000', ''
    except FileNotFoundError:
        print("⚠ 未找到stoken.txt文件，请创建该文件并填入cookie")
        return '0000000', ''
    except Exception as e:
        print(f"⚠ 读取stoken.txt失败: {e}")
        return '0000000', ''

# 加载配置
UID, COOKIE = load_stoken()

# 固定配置（写死在代码里）
CONFIG = {
    'uid': UID,
    'cookie': COOKIE,
    'x-rpc-device_id': 'd9951154-6eea-35e8-9e46-20c53f440ac7',
    'x-rpc-device_fp': '',
    'x-rpc-device_name': 'Xiaomi 2206123SC',
    'x-rpc-device_model': '2206123SC',
    'x-rpc-channel': 'xiaomi',
}

# DS签名Salt值 (从参考代码获取)
DS_SALT = '6s25p5ox5y14umn1p61aqyyvbvvl3lrt'

def generate_ds():
    """
    生成DS签名参数
    格式: timestamp,random_number,md5_hash
    Salt值: 6s25p5ox5y14umn1p61aqyyvbvvl3lrt
    """
    import hashlib
    import random
    
    t = str(int(time.time()))  # 当前时间戳(秒)
    r = str(random.randint(100001, 199999))  # 6位随机数
    # 计算MD5签名: salt={salt}&t={timestamp}&r={random}
    sign_str = f'salt={DS_SALT}&t={t}&r={r}'
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    
    return f'{t},{r},{sign}'
# HTTP请求头模板
DEFAULT_HEADERS = {
    'x-rpc-app_version': '2.86.0',
    'x-rpc-client_type': '2',
    'x-rpc-sdk_version': '2.35.0',
    'x-rpc-sys_version': '12',
    'x-rpc-app_id': 'bll8iq97cem8',
    'Referer': 'https://app.mihoyo.com',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 12; LIO-AN00 Build/TKQ1.220829.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/103.0.5060.129 Mobile Safari/537.36 miHoYoBBS/2.86.0',
    'Content-Type': 'application/json'
}

def get_headers(extra_headers=None):
    """
    获取完整的请求头
    :param extra_headers: 额外的请求头字典
    :return: 完整的请求头字典
    """
    headers = DEFAULT_HEADERS.copy()
    
    # 添加设备信息
    headers['x-rpc-device_id'] = CONFIG.get('x-rpc-device_id', '')
    headers['x-rpc-device_name'] = CONFIG.get('x-rpc-device_name', '')
    headers['x-rpc-device_model'] = CONFIG.get('x-rpc-device_model', '')
    headers['x-rpc-channel'] = CONFIG.get('x-rpc-channel', 'xiaomi')
    
    # 添加Cookie
    if CONFIG.get('cookie'):
        headers['Cookie'] = CONFIG['cookie']
    
    # 添加DS签名
    headers['DS'] = generate_ds()
    
    # 合并额外请求头
    if extra_headers:
        headers.update(extra_headers)
    
    return headers
 
# ==================== 性能优化配置 ====================
# 扫描间隔（毫秒）- 越小越快，但CPU占用越高
SCAN_INTERVAL = 0.01  # 10ms (原50ms)

# 是否启用极速模式（跳过部分检查）
ULTRA_FAST_MODE = True

# HTTP连接超时（秒）
HTTP_TIMEOUT = 5  # 减少超时时间，快速失败

# 最大重试次数
MAX_RETRIES = 2  # 减少重试次数，加快速度

# ==================== 窗口位置配置 ====================
# OpenCV预览窗口位置模式:
# 'center' - 屏幕中央（与红框重合，默认）
# 'custom' - 自定义位置（需要设置WINDOW_X和WINDOW_Y）
# 'top_right' - 右上角
# 'top_left' - 左上角
# 'bottom_right' - 右下角
# 'bottom_left' - 左下角
WINDOW_POSITION_MODE = 'custom'  # 改为'custom'使用自定义位置

# 自定义窗口位置（仅在WINDOW_POSITION_MODE='custom'时生效）
WINDOW_X = 100   # 距离屏幕左边的像素
WINDOW_Y = 100   # 距离屏幕顶边的像素

# 是否在窗口标题显示FPS
SHOW_FPS_IN_TITLE = True

# ==================== 全局配置 ====================
# 扫描窗口配置（逻辑像素，不受DPI影响）
SCAN_WIN_WIDTH = 300
SCAN_WIN_HEIGHT = 300

def calculate_window_position(mode, screen_width, screen_height, win_width, win_height):
    """
    计算窗口位置
    :param mode: 位置模式
    :param screen_width: 屏幕宽度
    :param screen_height: 屏幕高度
    :param win_width: 窗口宽度
    :param win_height: 窗口高度
    :return: (x, y) 坐标
    """
    if mode == 'center':
        # 屏幕中央
        x = (screen_width // 2) - (win_width // 2)
        y = (screen_height // 2) - (win_height // 2)
    elif mode == 'top_right':
        # 右上角
        x = screen_width - win_width - 20
        y = 20
    elif mode == 'top_left':
        # 左上角
        x = 20
        y = 20
    elif mode == 'bottom_right':
        # 右下角
        x = screen_width - win_width - 20
        y = screen_height - win_height - 50  # 留出任务栏空间
    elif mode == 'bottom_left':
        # 左下角
        x = 20
        y = screen_height - win_height - 50
    elif mode == 'custom':
        # 自定义位置
        x = WINDOW_X
        y = WINDOW_Y
    else:
        # 默认居中
        x = (screen_width // 2) - (win_width // 2)
        y = (screen_height // 2) - (win_height // 2)
    
    return x, y

# 获取DPI缩放比例
DPI_SCALE = get_dpi_scale()
print(f"检测到DPI缩放比例: {DPI_SCALE} ({int(DPI_SCALE*100)}%)")

# 计算实际物理像素（考虑DPI缩放）
PHYSICAL_WIDTH = int(SCAN_WIN_WIDTH * DPI_SCALE)
PHYSICAL_HEIGHT = int(SCAN_WIN_HEIGHT * DPI_SCALE)

if DPI_SCALE != 1.0:
    print(f"物理像素尺寸: {PHYSICAL_WIDTH}x{PHYSICAL_HEIGHT}")
    print("已自动适配DPI缩放")

# 显示框框 启动线程
def show_scan_frame():
    """显示扫描框窗口"""
    try:
        import kuang  # 修正模块名
    except ImportError as e:
        print(f"警告: 无法导入kuang模块 - {e}")
        print("请确保kuang.py文件存在")

my_thread = threading.Thread(target=show_scan_frame, daemon=True)
my_thread.start()
time.sleep(0.5)  # 等待窗口初始化

# 获取屏幕坐标（与kuang.py保持一致）
root = tk.Tk()
root.withdraw()  # 隐藏主窗口
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# 红框窗口位置（始终居中）
frame_x = (screen_width // 2) - (PHYSICAL_WIDTH // 2)
frame_y = (screen_height // 2) - (PHYSICAL_HEIGHT // 2)
root.destroy()  # 销毁临时窗口

# OpenCV预览窗口位置（根据配置）
window_x, window_y = calculate_window_position(
    WINDOW_POSITION_MODE, 
    screen_width, 
    screen_height, 
    PHYSICAL_WIDTH, 
    PHYSICAL_HEIGHT
)

# 设置扫描区域左上角的坐标和宽高（使用物理像素，基于红框位置）
left, top = frame_x, frame_y
right = left + PHYSICAL_WIDTH
bottom = top + PHYSICAL_HEIGHT

print(f"红框位置: ({frame_x}, {frame_y})")
print(f"预览窗口位置: ({window_x}, {window_y})")
print(f"扫描区域: ({left}, {top}) 到 ({right}, {bottom})")
print(f"逻辑大小: {SCAN_WIN_WIDTH}x{SCAN_WIN_HEIGHT}")
print(f"物理大小: {PHYSICAL_WIDTH}x{PHYSICAL_HEIGHT}")

# 创建OpenCV窗口并设置位置（使用自定义位置）
cv2.namedWindow("QR Code Scanner", cv2.WINDOW_NORMAL)
cv2.resizeWindow("QR Code Scanner", PHYSICAL_WIDTH, PHYSICAL_HEIGHT)
cv2.moveWindow("QR Code Scanner", window_x, window_y)
 
 
# 抢码开始 (Scan) - 极速版
def Request(ticket, app_id=4, max_retries=None):
    """
    扫描二维码认主 - 第一步（极速优化版）
    :param ticket: 二维码中的ticket参数
    :param app_id: 应用ID (原神为4)
    :param max_retries: 最大重试次数（默认使用全局配置）
    :return: retcode (0表示成功)
    """
    if max_retries is None:
        max_retries = MAX_RETRIES
    
    for attempt in range(max_retries):
        try:
            conn = http.client.HTTPSConnection("api-sdk.mihoyo.com", timeout=HTTP_TIMEOUT)
            payload = json.dumps({
                "app_id": app_id,
                "device": CONFIG.get('x-rpc-device_id', ''),
                "ticket": ticket
            }, separators=(',', ':'))  # 紧凑JSON，减少数据量
            
            headers = get_headers()
            
            conn.request("POST", "/hk4e_cn/combo/panda/qrcode/scan", payload, headers)
            res = conn.getresponse()
            data = res.read()
            data = json.loads(data.decode("utf-8"))
            retcode = data.get("retcode", -1)
            
            if retcode == 0:
                if not ULTRA_FAST_MODE:
                    print("✓ 抢码成功")
                return retcode
            else:
                if not ULTRA_FAST_MODE or attempt == max_retries - 1:
                    message = data.get("message", "未知错误")
                    print(f"✗ 抢码失败 [{retcode}]: {message}")
                
        except Exception as e:
            if not ULTRA_FAST_MODE or attempt == max_retries - 1:
                print(f"✗ 抢码异常: {str(e)}")
        
        if attempt < max_retries - 1:
            time.sleep(0.1)  # 极速模式：更短的重试间隔
    
    return -1
 
 
# 确认登陆 (Confirm) - 极速版
def ConfirmRequest(ticket, app_id=4):
    """
    确认登录 - 第二步（极速优化版）
    :param ticket: 二维码中的ticket参数
    :param app_id: 应用ID
    :return: 是否成功
    """
    uid = CONFIG['uid']
    
    if not CONFIG['cookie']:
        print("⚠ 错误: Cookie未配置")
        return False
    
    try:
        if not ULTRA_FAST_MODE:
            print("正在获取game_token...")
        
        # 第一步: 获取game_token（使用更短的超时）
        conn = http.client.HTTPSConnection("api-takumi.miyoushe.com", timeout=HTTP_TIMEOUT)
        headers = get_headers()
        
        conn.request("GET", f"/auth/api/getGameToken?uid={uid}", '', headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        
        if data.get("retcode") != 0:
            if not ULTRA_FAST_MODE:
                print(f"✗ 获取token失败 [{data.get('retcode')}]")
            return False
        
        token = data["data"]["game_token"]
        
        if not ULTRA_FAST_MODE:
            print("正在确认登录...")
        
        # 第二步: 确认登录（紧凑JSON）
        conn = http.client.HTTPSConnection("api-sdk.mihoyo.com", timeout=HTTP_TIMEOUT)
        payload = json.dumps({
            "app_id": app_id,
            "device": CONFIG.get('x-rpc-device_id', ''),
            "payload": {
                "proto": "Account",
                "raw": json.dumps({"uid": uid, "token": token}, separators=(',', ':'))
            },
            "ticket": ticket
        }, separators=(',', ':'))
        
        headers = get_headers()
        conn.request("POST", "/hk4e_cn/combo/panda/qrcode/confirm", payload, headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        
        if data.get("retcode") == 0:
            if not ULTRA_FAST_MODE:
                print("✓ 确认登录成功！")
            return True
        else:
            if not ULTRA_FAST_MODE:
                print(f"✗ 确认登录失败 [{data.get('retcode')}]")
            return False
            
    except Exception as e:
        if not ULTRA_FAST_MODE:
            print(f"✗ 确认登录异常: {str(e)}")
        return False


# 云游戏登录 (Cloud Game Login)
def CloudGameLogin(tk, token_types):
    """
    云游戏扫码登录
    :param tk: 二维码中的tk参数
    :param token_types: token类型
    :return: 登录结果字典
    """
    uid = CONFIG['uid']
    
    if not CONFIG['cookie']:
        print("⚠ 错误: 请先在CONFIG中配置cookie")
        return None
    
    try:
        print("正在进行云游戏登录...")
        
        # 构建云游戏专用请求头
        cloud_headers = {
            'x-rpc-app_version': '2.86.0',
            'x-rpc-client_type': '2',
            'x-rpc-sdk_version': '2.35.0',
            'x-rpc-device_id': CONFIG.get('x-rpc-device_id', ''),
            'x-rpc-device_name': CONFIG.get('x-rpc-device_name', ''),
            'x-rpc-device_model': CONFIG.get('x-rpc-device_model', ''),
            'x-rpc-channel': CONFIG.get('x-rpc-channel', 'xiaomi'),
            'x-rpc-sys_version': '12',
            'x-rpc-app_id': 'bll8iq97cem8',
            'Referer': 'https://app.mihoyo.com',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; LIO-AN00 Build/TKQ1.220829.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/103.0.5060.129 Mobile Safari/537.36 miHoYoBBS/2.86.0',
            'Content-Type': 'application/json',
            'Cookie': CONFIG['cookie'],
            'Host': 'passport-api.mihoyo.com'
        }
        
        # 第一步: Scan QR Login
        print("  [1/2] 扫描QR码...")
        conn = http.client.HTTPSConnection("passport-api.mihoyo.com", timeout=10)
        
        # 确保token_types是整数列表
        payload_data = {
            "ticket": tk,
            "token_types": [int(token_types)]
        }
        payload = json.dumps(payload_data)
        
        # 添加DS签名
        cloud_headers['DS'] = generate_ds()
        
        print(f"  请求数据: {payload}")
        print(f"  请求头DS: {cloud_headers['DS']}")
        
        conn.request("POST", "/account/ma-cn-passport/app/scanQRLogin", payload, cloud_headers)
        res = conn.getresponse()
        response_data = res.read().decode("utf-8")
        print(f"  响应状态: {res.status}")
        print(f"  响应内容: {response_data[:200]}")
        
        data = json.loads(response_data)
        
        if data.get("retcode") != 0:
            print(f"✗ 云游戏扫描失败: [{data.get('retcode')}] {data.get('message', '未知错误')}")
            return None
        
        print("  ✓ 扫描成功")
        
        # 第二步: Confirm QR Login
        print("  [2/2] 确认QR码...")
        conn = http.client.HTTPSConnection("passport-api.mihoyo.com", timeout=10)
        
        # 重新生成DS签名
        cloud_headers['DS'] = generate_ds()
        
        conn.request("POST", "/account/ma-cn-passport/app/confirmQRLogin", payload, cloud_headers)
        res = conn.getresponse()
        response_data = res.read().decode("utf-8")
        print(f"  响应状态: {res.status}")
        print(f"  响应内容: {response_data[:200]}")
        
        data = json.loads(response_data)
        
        if data.get("retcode") == 0:
            app_name = data.get('data', {}).get('app_name', '未知应用')
            print(f"✓ 云游戏登录成功! 应用: {app_name}")
            return {
                'success': True,
                'uid': uid,
                'game': f'[云游戏]{app_name}'
            }
        else:
            print(f"✗ 云游戏确认失败: [{data.get('retcode')}] {data.get('message', '未知错误')}")
            return None
            
    except Exception as e:
        print(f"✗ 云游戏登录异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
 
 
print("="*50)
print("原神抢码登录工具 v2.2 (极速版)")
print("="*50)
print(f"扫描间隔: {SCAN_INTERVAL*1000:.0f}ms")
print(f"HTTP超时: {HTTP_TIMEOUT}s")
print(f"极速模式: {'开启' if ULTRA_FAST_MODE else '关闭'}")
print("="*50)
print("请将游戏登录二维码放在屏幕中央的红色方框内")
print("按任意键退出程序")
print("="*50)

# 检查配置
if not CONFIG['cookie']:
    print("\n⚠ 警告: Cookie未配置!")
    print("请在 main.py 的 CONFIG 中填写cookie")
    print("或者运行: python config_helper.py")
    print("\n按回车键继续...")
    input()

scanned_tickets = set()  # 记录已扫描的ticket，避免重复处理
scan_count = 0  # 扫描次数统计
last_scan_time = time.time()  # 上次扫描时间
fps_counter = 0  # FPS计数器
fps_start_time = time.time()  # FPS计算起始时间
current_fps = 0  # 当前FPS

while True:
    try:
        scan_count += 1
        
        # 截取指定区域的屏幕截图
        screenshot = cv2.cvtColor(
            np.array(ImageGrab.grab(bbox=(left, top, right, bottom))),
            cv2.COLOR_BGR2RGB
        )
 
        # 将截图转换为灰度图像
        gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
 
        # 尝试使用pyzbar库识别二维码
        codes = decode(gray, symbols=[pyzbar.ZBarSymbol.QRCODE])
 
        # 如果找到了二维码，输出其内容
        if codes:
            qr_content = codes[0].data.decode()
            
            # 解析URL参数
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(qr_content)
            params = parse_qs(parsed_url.query)
            
            ticket = params.get('ticket', [None])[0]
            tk = params.get('tk', [None])[0]
            token_types = params.get('token_types', [None])[0]
            expire = params.get('expire', [None])[0]
            app_id = params.get('app_id', [None])[0]
            app_name = params.get('app_name', ['未知应用'])[0]
            
            # 检查二维码是否过期
            if expire:
                try:
                    expire_time = int(expire)
                    current_time = int(time.time())
                    if current_time > expire_time:
                        if not ULTRA_FAST_MODE:
                            print("\n⚠ 二维码已过期")
                        continue
                except:
                    pass
            
            # 判断是云游戏还是普通登录
            if tk and token_types:
                # 云游戏登录
                ticket_id = tk
                if ticket_id in scanned_tickets:
                    continue
                
                if not ULTRA_FAST_MODE:
                    print(f"\n检测到云游戏二维码 [TK: {tk[:16]}...]")
                else:
                    print(f"\n[抢码] 云游戏二维码 detected!")
                
                scanned_tickets.add(ticket_id)
                start_time = time.time()
                
                result = CloudGameLogin(tk, int(token_types))
                elapsed = time.time() - start_time
                
                if result and result.get('success'):
                    print(f"\n{'='*50}")
                    print(f"🎉 云游戏登录成功！耗时: {elapsed:.3f}s")
                    print(f"   UID: {result['uid']}")
                    print(f"   应用: {result['game']}")
                    print(f"{'='*50}")
                    break
                else:
                    if not ULTRA_FAST_MODE:
                        print("云游戏登录失败，继续等待...")
                    scanned_tickets.discard(ticket_id)
                    
            elif ticket and app_id:
                # 普通游戏登录
                if ticket in scanned_tickets:
                    continue
                
                if not ULTRA_FAST_MODE:
                    print(f"\n检测到游戏二维码 [Ticket: {ticket[:16]}...]")
                else:
                    print(f"\n[抢码] 游戏二维码 detected! Ticket: {ticket[:12]}...")
                
                scanned_tickets.add(ticket)
                start_time = time.time()
                
                # 进入抢码（极速模式）
                retcode = Request(ticket, int(app_id))
                
                if retcode == 0:
                    elapsed_scan = time.time() - start_time
                    if not ULTRA_FAST_MODE:
                        print(f"⏱ 抢码成功，耗时: {elapsed_scan:.3f}s")
                    else:
                        print(f"[抢码] ✓ Scan成功 ({elapsed_scan:.3f}s)")
                    
                    # 立即确认登陆
                    success = ConfirmRequest(ticket, int(app_id))
                    elapsed_total = time.time() - start_time
                    
                    if success:
                        print(f"\n{'='*50}")
                        print(f"🎉 登录完成！总耗时: {elapsed_total:.3f}s")
                        print(f"{'='*50}")
                        break
                    else:
                        if not ULTRA_FAST_MODE:
                            print("登录失败，继续等待...")
                        scanned_tickets.discard(ticket)
                else:
                    if not ULTRA_FAST_MODE:
                        print(f"抢码失败，继续等待...")
                    scanned_tickets.discard(ticket)
            else:
                if not ULTRA_FAST_MODE:
                    print("\n⚠ 无效的二维码格式")

        # 动态调整扫描间隔（极速模式）
        if ULTRA_FAST_MODE:
            time.sleep(SCAN_INTERVAL)  # 10ms
        else:
            time.sleep(0.05)  # 50ms (原速度)
        
        # 计算FPS
        fps_counter += 1
        elapsed = time.time() - fps_start_time
        if elapsed >= 1.0:  # 每秒更新一次FPS
            current_fps = int(fps_counter / elapsed)
            fps_counter = 0
            fps_start_time = time.time()
            
            # 更新窗口标题显示FPS
            if SHOW_FPS_IN_TITLE:
                cv2.setWindowTitle("QR Code Scanner", f"QR Code Scanner - {current_fps} FPS")
 
        # 在窗口中显示截图
        cv2.imshow("QR Code Scanner", screenshot)
 
        # 检查是否按下了键盘上的任意键
        if cv2.waitKey(1) != -1:
            break
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        break
    except Exception as e:
        if not ULTRA_FAST_MODE:
            print(f"发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
        time.sleep(0.1)

# 关闭窗口
cv2.destroyAllWindows()
print("\n程序已退出")
 