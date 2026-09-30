# VBot Assistant

Yêu cầu Home Assistant **2026.8.0 trở lên** vì integration có Media Browser Search.

Tài liệu sử dụng đầy đủ của integration được duy trì tại
[`../../README.md`](../../README.md), bao gồm:

- cài đặt và cấu hình nhiều loa;
- Media Player, volume, mute, seek, next/previous;
- service `vbot_assistant.say`;
- Conversation Agent với chế độ `chatbot` và `processing`;
- ví dụ Lovelace, script và automation;
- MQTT topics và hướng dẫn xử lý sự cố.

Phiên bản `1.9.1` hỗ trợ loa chủ VBot, Phicomm R1 Client và ESP32/ESP32-S3
Client; gồm runtime riêng từng Config Entry, Update Entity, Reconfigure/Reauth,
native Multiroom, Device Trigger và TTS target nhiều thiết bị. Availability dùng
một coordinator cho mỗi thiết bị và MQTT Client ID được chống trùng không phân
biệt chữ hoa/chữ thường.

Các binary sensor kết nối MQTT, microphone và Bluetooth được tạo ở trạng thái
tắt mặc định; có thể bật từ trang thiết bị. Lỗi API key, trùng MQTT Client ID và
Media API cũ được hiển thị trong **Cài đặt → Hệ thống → Sửa chữa**.
