# Changelog

## 1.3.1

- Thêm Text và Button Google Translate TTS cho ESP32/ESP32-S3 qua MQTT; âm
  thanh HTTPS được ESP32 chuyển qua `audio_proxy` đã cấu hình.
- Thêm Text và Button nhập URL file âm thanh cho ESP32; file HTTP trong LAN
  được phát trực tiếp, URL HTTPS hoặc URL cần phân giải đi qua `audio_proxy`.
- Hỗ trợ profile riêng cho loa chủ VBot, Phicomm R1 và ESP32/ESP32-S3.
- Chuẩn hóa URL API khi nhập có/không `http://` hoặc dấu `/` cuối.
- Tự áp dụng port mặc định `5002` cho loa chủ và `8081` cho Phicomm R1.
- Giữ ESP32 ở HTTP cổng 80 khi người dùng không nhập port.
- Thêm tùy chọn tự động cập nhật URL API qua mDNS.
- Cập nhật đúng Config Entry theo `device_id` khi thiết bị đổi IP, không tạo
  entity hoặc thiết bị trùng.
- Thêm cảm biến chẩn đoán URL hiện tại, nguồn URL và lần cập nhật mDNS.
- Thêm migration Config Entry phiên bản 2; giữ an toàn cấu hình cũ ở chế độ
  URL thủ công.
- Giữ nguyên URL/port tùy chỉnh do người dùng nhập.

## 1.3.0

- Phiên bản nền trước khi bổ sung cơ chế URL API đa thiết bị và migration v2.
