import webview

window = webview.create_window(
    "ConcentrateOn",
    "./pages/focus.html",
    min_size=(600, 800),
)

webview.start()
