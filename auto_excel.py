import os
import time
import requests
import pandas as pd
import tomllib
from openai import OpenAI

EXCEL_FILE = "du_lieu_mau.xlsx"
API_BASE_URL = "http://127.0.0.1:8080/api/v1"

def create_template_if_not_exists():
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame({
            "Chủ đề": ["Lợi ích của việc dậy sớm"],
            "Phong cách": ["Hài hước, năng động"],
            "Nội dung mẫu": ["Dậy sớm giúp bạn làm được nhiều việc hơn. Cơ thể khỏe mạnh, đầu óc minh mẫn. Đừng ngủ nướng nữa!"],
            "Trạng thái": [""]
        })
        df.to_excel(EXCEL_FILE, index=False)
        print(f"Đã tạo file mẫu: {EXCEL_FILE}")

def load_config():
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    return config

def generate_script(client, chu_de, phong_cach, noi_dung_mau):
    prompt = f"""
Tôi muốn tạo một kịch bản video ngắn (Shorts/TikTok) về chủ đề: "{chu_de}".
Vui lòng tham khảo nội dung mẫu sau: "{noi_dung_mau}".
Yêu cầu phong cách: {phong_cach}.

Lưu ý: 
- Không copy nguyên văn nội dung mẫu, hãy diễn đạt lại cho cuốn hút, sinh động và giữ độ dài phù hợp (khoảng 30-60 giây đọc).
- Chỉ trả về nội dung kịch bản, không kèm theo lời chào hay giải thích gì thêm.
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "Bạn là một chuyên gia viết kịch bản video TikTok/Shorts viral."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

def create_video_task(chu_de, video_script):
    payload = {
        "video_subject": chu_de,
        "video_script": video_script,
        "video_aspect": "9:16",
        "video_concat_mode": "random",
        "video_clip_duration": 5,
        "video_count": 1
    }
    try:
        response = requests.post(f"{API_BASE_URL}/videos", json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 200:
                return data["data"]["task_id"]
        print("Lỗi khi tạo task:", response.text)
    except Exception as e:
        print("Lỗi kết nối tới MoneyPrinterTurbo API:", e)
    return None

def wait_for_task(task_id, current_info=""):
    while True:
        try:
            response = requests.get(f"{API_BASE_URL}/tasks/{task_id}", timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 200:
                    task_data = data["data"]
                    progress = task_data.get("progress", 0)
                    state = task_data.get("state", 0)
                    info_str = f" {current_info}" if current_info else ""
                    print(f"Đang render video... {progress}%{info_str}")
                    
                    # state 1 is success, -1 is failed
                    if state == 1 or progress >= 100:
                        print("Task hoàn thành!")
                        return True
                    elif state == -1:
                        print("Task thất bại!")
                        return False
        except Exception as e:
            print("Lỗi khi kiểm tra trạng thái:", e)
            
        time.sleep(5)

def main():
    print("Khởi động hệ thống Auto Excel Pipeline...")
    create_template_if_not_exists()
    
    try:
        config = load_config()
        # Ưu tiên lấy cấu hình DeepSeek
        api_key = config.get("app", {}).get("deepseek_api_key", "")
        base_url = config.get("app", {}).get("deepseek_base_url", "https://api.deepseek.com")
        
        # Nếu không có DeepSeek, thử lấy OpenAI
        if not api_key:
            api_key = config.get("app", {}).get("openai_api_key", "")
            base_url = config.get("app", {}).get("openai_base_url", "")
            
    except Exception as e:
        print("Không thể đọc config.toml:", e)
        return
        
    if not api_key:
        print("Lỗi: Vui lòng điền deepseek_api_key hoặc openai_api_key vào file config.toml trước khi chạy.")
        return

    # DeepSeek tương thích hoàn toàn với thư viện OpenAI
    client = OpenAI(api_key=api_key)
    if base_url:
        client.base_url = base_url

    try:
        df = pd.read_excel(EXCEL_FILE)
    except Exception as e:
        print(f"Lỗi khi đọc file {EXCEL_FILE}:", e)
        return
    
    if "Trạng thái" not in df.columns:
        df["Trạng thái"] = ""

    has_work = False
    for index, row in df.iterrows():
        trang_thai = str(row.get("Trạng thái", "")).strip()
        if trang_thai == "Hoàn thành":
            continue
            
        chu_de = str(row.get("Chủ đề", "")).strip()
        phong_cach = str(row.get("Phong cách", "")).strip()
        noi_dung_mau = str(row.get("Nội dung mẫu", "")).strip()
        
        if not chu_de or chu_de == "nan":
            continue
            
        has_work = True
        print(f"\n--- Bắt đầu xử lý dòng {index + 1}: {chu_de} ---")
        print("Đang nhờ ChatGPT viết lại kịch bản...")
        try:
            video_script = generate_script(client, chu_de, phong_cach, noi_dung_mau)
            print(f"Kịch bản mới:\n{video_script}\n")
        except Exception as e:
            print("Lỗi khi gọi ChatGPT:", e)
            df.at[index, "Trạng thái"] = "Lỗi gọi ChatGPT"
            df.to_excel(EXCEL_FILE, index=False)
            continue
            
        print("Đang gửi lệnh tạo video tới MoneyPrinterTurbo...")
        task_id = create_video_task(chu_de, video_script)
        
        if task_id:
            print(f"Đã tạo Task ID: {task_id}")
            success = wait_for_task(task_id, f"({index + 1}/{len(df)})")
            if success:
                df.at[index, "Trạng thái"] = "Hoàn thành"
            else:
                df.at[index, "Trạng thái"] = "Lỗi render"
        else:
            df.at[index, "Trạng thái"] = "Lỗi kết nối API"
            
        # Lưu kết quả vào Excel ngay sau khi xong 1 dòng
        df.to_excel(EXCEL_FILE, index=False)
        print("Đã lưu trạng thái vào file Excel.")
        
    if not has_work:
        print("Tất cả các dòng trong file Excel đều đã được xử lý (hoặc không có dữ liệu mới).")

if __name__ == "__main__":
    main()
