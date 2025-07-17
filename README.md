# VBot-Assistant-MQTT-HASS
Tích Hợp VBot Assistant Tới Home Assistant (HASS) Thông Qua Giao Thức MQTT

Trang Chính VBot Assistant: https://github.com/marion001/VBot_Offline

## Cài Đặt
1. Cài đặt [bằng cách đăng ký làm kho lưu trữ tùy chỉnh của HACS thêm trực tiếp url]
     - đi tới HACS -> Kho lưu trữ tùy chỉnh ->Thêm URL: [https://github.com/marion001/VBot-Assist-Conversation.git](https://github.com/marion001/VBot-Assistant-MQTT-HASS.git) -> chọn Kiểu là: "Bộ Tích Hợp" -> nhấn "Thêm"

2. Sau khi thêm URL xong bạn hãy tìm kiếm từ khóa: "VBot Assistant MQTT" trong HACS hãy tải xuống cài đặt nó
3. Khởi động lại Home Assistant khi đã cài đặt xong "VBot Assistant MQTT"
4. Đi tới: Cài đặt > Thiết bị & Dịch vụ
5. Ở góc dưới cùng bên phải, chọn nút Thêm tích hợp -> tìm kiếm với tên: "VBot Assistant MQTT" và chọn
6. Điền tên Client từ Cấu Hình Kết Nối MQTT của UI VBot vào ô: "Nhập Tên Client tương ứng trong (Cấu Hình Config -> Cấu Hình Kết Nối MQTT Broker) của loa VBot" -> Gửi đi
7. Sau khi hoàn tất các bước sẽ tự động có các thực thể entity id xuất hiện
       

