import webview

class TodoAPI:
    def get_todos(self):
        return ["学习 PyWebView", "写一个浮窗"]

api = TodoAPI()

# 正确做法：直接在 create_window 中设置
window = webview.create_window(
    title='Todo Floating Window',
    url='index.html',       
    js_api=api,             
    width=320,
    height=450,
    frameless=True,         # 无边框
    on_top=True,            # 置顶
    # 关键点 1：不要写 hex 颜色，直接设置为透明关键字（支持空字符串、'transparent' 或不写）
    # pywebview 内部会识别并开启底层窗口的透明通道
    # background_color='transparent' 
)

# 关键点 2：start() 保持干净，不要加任何自定义参数
webview.start(debug=True)