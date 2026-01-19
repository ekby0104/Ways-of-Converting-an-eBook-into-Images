import tkinter as tk
from tkinter import messagebox
import threading
import queue
import time
from datetime import datetime

import mss
import mss.tools
from pynput import mouse


# ================= 앱 정보 =================
APP_NAME = "Screen Capture Tool"
APP_VERSION = "1.0"


# ================= Tk 초기화 =================
root = tk.Tk()
root.title(f"{APP_NAME} v{APP_VERSION}")
root.geometry("420x380")
root.resizable(False, False)


# ================= 상태 =================
coords = {
    "lt": None,
    "rb": None,
    "next": None
}


# ================= Overlay =================
def create_overlay():
    overlay = tk.Toplevel(root)
    overlay.overrideredirect(True)
    overlay.attributes("-topmost", True)
    overlay.attributes("-alpha", 0.35)
    overlay.configure(bg="black")

    label = tk.Label(
        overlay,
        text="좌표: (0, 0)\n왼쪽 클릭: 선택\n오른쪽 클릭: 취소",
        fg="white",
        bg="black",
        font=("Segoe UI", 11)
    )
    label.pack(padx=10, pady=10)

    overlay.geometry("+20+20")
    return overlay, label


# ================= 마우스 입력 워커 =================
def mouse_pick_worker(result_queue):
    result = {"pos": None, "cancel": False}

    def on_move(x, y):
        result_queue.put(("move", (x, y)))

    def on_click(x, y, button, pressed):
        if not pressed:
            return

        if button == mouse.Button.right:
            result["cancel"] = True
            result_queue.put(("done", result))
            return False

        if button == mouse.Button.left:
            result["pos"] = (x, y)
            result_queue.put(("done", result))
            return False

    with mouse.Listener(on_move=on_move, on_click=on_click) as listener:
        listener.join()


# ================= 공용 좌표 선택 =================
def pick_point(message, on_done):
    def start():
        messagebox.showinfo(
            "좌표 선택",
            message + "\n\n왼쪽 클릭: 선택\n오른쪽 클릭: 취소"
        )

        root.withdraw()
        overlay, label = create_overlay()

        q = queue.Queue()

        threading.Thread(
            target=mouse_pick_worker,
            args=(q,),
            daemon=True
        ).start()

        def poll():
            try:
                while True:
                    msg, data = q.get_nowait()

                    if msg == "move":
                        x, y = data
                        label.config(
                            text=f"좌표: ({x}, {y})\n왼쪽 클릭: 선택\n오른쪽 클릭: 취소"
                        )

                    elif msg == "done":
                        overlay.destroy()
                        root.deiconify()

                        if data["cancel"]:
                            on_done(None)
                        else:
                            on_done(data["pos"])
                        return
            except queue.Empty:
                pass

            root.after(10, poll)

        poll()

    # 🔑 이벤트 루프에 작업을 묶어 exe 종료 방지
    root.after(0, start)


# ================= 캡처 =================
def capture_area(x1, y1, x2, y2):
    with mss.mss() as sct:
        monitor = {
            "left": min(x1, x2),
            "top": min(y1, y2),
            "width": abs(x2 - x1),
            "height": abs(y2 - y1)
        }
        img = sct.grab(monitor)
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        mss.tools.to_png(img.rgb, img.size, output=filename)


# ================= UI 핸들러 =================
def set_coord(key, point, label):
    if point is None:
        return
    coords[key] = point
    label.config(text=str(point))


def pick_left_top():
    pick_point(
        "캡처 영역의 왼쪽 위 지점을 클릭하세요.",
        lambda p: set_coord("lt", p, lbl_lt)
    )


def pick_right_bottom():
    pick_point(
        "캡처 영역의 오른쪽 아래 지점을 클릭하세요.",
        lambda p: set_coord("rb", p, lbl_rb)
    )


def pick_next_page():
    pick_point(
        "다음 페이지로 이동할 위치를 클릭하세요.",
        lambda p: set_coord("next", p, lbl_np)
    )


def run_capture():
    if not all(coords.values()):
        messagebox.showerror("오류", "모든 좌표를 설정하세요.")
        return

    try:
        pages = int(ent_pages.get())
        delay = float(ent_delay.get())
    except ValueError:
        messagebox.showerror("오류", "페이지 수와 지연 시간은 숫자여야 합니다.")
        return

    def task():
        ctrl = mouse.Controller()

        for _ in range(pages):
            capture_area(*coords["lt"], *coords["rb"])
            time.sleep(delay)
            ctrl.position = coords["next"]
            ctrl.click(mouse.Button.left, 1)
            time.sleep(delay)

        messagebox.showinfo("완료", "모든 캡처가 완료되었습니다.")

    threading.Thread(target=task, daemon=True).start()


# ================= UI =================
tk.Button(root, text="왼쪽 위 좌표 선택", command=pick_left_top).pack(pady=4)
lbl_lt = tk.Label(root, text="-")
lbl_lt.pack()

tk.Button(root, text="오른쪽 아래 좌표 선택", command=pick_right_bottom).pack(pady=4)
lbl_rb = tk.Label(root, text="-")
lbl_rb.pack()

tk.Button(root, text="다음 페이지 클릭 좌표", command=pick_next_page).pack(pady=4)
lbl_np = tk.Label(root, text="-")
lbl_np.pack()

frm = tk.Frame(root)
frm.pack(pady=12)

tk.Label(frm, text="페이지 수").grid(row=0, column=0, padx=5)
ent_pages = tk.Entry(frm, width=6)
ent_pages.insert(0, "1")
ent_pages.grid(row=0, column=1)

tk.Label(frm, text="지연(초)").grid(row=0, column=2, padx=5)
ent_delay = tk.Entry(frm, width=6)
ent_delay.insert(0, "1")
ent_delay.grid(row=0, column=3)

tk.Button(root, text="캡처 시작", command=run_capture, height=2).pack(pady=14)

root.mainloop()
