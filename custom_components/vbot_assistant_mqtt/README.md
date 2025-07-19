# VBot-Assistant-MQTT-HASS
Custom Component Tích Hợp VBot Assistant Tới Home Assistant (HASS) Thông Qua Giao Thức MQTT

Trang Chính VBot Assistant: https://github.com/marion001/VBot_Offline
- Group Hệ Hỗ Trợ: [Facebook - Group](https://www.facebook.com/groups/1148385343358824)
- [Facebook - Vũ Tuyển](https://www.facebook.com/TWFyaW9uMDAx)

## Cài Đặt
0. Yêu Cầu: Trong Cấu Hình Config Của Loa VBot Phải Bật -> Cấu Hình Kết Nối MQTT Broker Nhé
1. Cài đặt [bằng cách đăng ký làm kho lưu trữ tùy chỉnh của HACS thêm trực tiếp url]
     - đi tới HACS -> Kho lưu trữ tùy chỉnh ->Thêm URL: [https://github.com/marion001/VBot-Assist-Conversation.git](https://github.com/marion001/VBot-Assistant-MQTT-HASS.git) -> chọn Kiểu là: "Bộ Tích Hợp" -> nhấn "Thêm"

2. Sau khi thêm URL xong bạn hãy tìm kiếm từ khóa: "VBot Assistant MQTT" trong HACS hãy tải xuống cài đặt nó
3. Khởi động lại Home Assistant khi đã cài đặt xong "VBot Assistant MQTT"
4. Đi tới: Cài đặt -> Thiết bị & Dịch vụ
	- hoặc nhấn vào đây: [![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=vbot_assistant_mqtt)
5. Ở góc dưới cùng bên phải, chọn nút Thêm tích hợp -> tìm kiếm với tên: "VBot Assistant MQTT" và chọn
6. Điền tên Client từ Cấu Hình Kết Nối MQTT của UI VBot vào ô: "Nhập Tên Client tương ứng trong (Cấu Hình Config -> Cấu Hình Kết Nối MQTT Broker) của loa VBot" -> Gửi đi
7. Sau khi hoàn tất các bước sẽ tự động có các thực thể entity id xuất hiện
8. Bạn có thể thêm nhiều thiết bị Loa VBot vào Home Assistant (HASS) bằng cách nhấn vào:
    - Cài đặt -> Thiết bị & Dịch vụ -> VBot Assistant MQTT -> Thêm Mục -> điền tên Client MQTT của loa VBot khác vào
       

<img width="1911" height="915" alt="Image" src="https://github.com/user-attachments/assets/5ed4cfb8-6b05-428d-959c-328149373f60" />
<img width="1901" height="909" alt="Image" src="https://github.com/user-attachments/assets/b2437e4c-d41c-46b2-a094-a3d136001448" />
<img width="1887" height="901" alt="Image" src="https://github.com/user-attachments/assets/74429691-9bb3-49b1-b72d-ea136776c33d" />
<img width="1913" height="919" alt="Image" src="https://github.com/user-attachments/assets/3189100c-afe1-4fe7-81dd-d17a4a0df770" />
