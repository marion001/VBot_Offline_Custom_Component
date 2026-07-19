# VBot Assistant cho Home Assistant

Custom component kết nối một hoặc nhiều loa VBot với Home Assistant qua MQTT và API.

## Chức năng

- Media Player: play, pause, resume, stop, next, previous, seek, volume và mute.
- Đồng bộ tên bài, nguồn phát, nghệ sĩ, album, ảnh bìa, thời lượng và trạng thái online.
- Điều khiển nhạc nội bộ, playlist, AirPlay và Bluetooth theo khả năng của từng nguồn.
- Phát TTS bằng Text + Button hoặc service `tts_vbot_assistant.say`.
- Dùng VBot làm Conversation Agent cho Home Assistant Assist.
- Điều khiển các switch cấu hình VBot, âm lượng, LED và nguồn nội dung.
- Hiển thị phiên bản chương trình/giao diện VBot và kiểm tra cập nhật.
- Hỗ trợ nhiều loa; mỗi loa được phân biệt bằng MQTT Client Name.

## Yêu cầu

1. VBot và Home Assistant truy cập được cùng MQTT Broker.
2. MQTT Broker đã được cấu hình và bật trong `Config.json` của từng loa.
3. Mỗi loa phải có `mqtt_client_name` riêng, ví dụ `VBot_Phong_Khach`.
4. API VBot phải truy cập được từ Home Assistant, ví dụ `192.168.1.20:5002`.

## Cài đặt bằng HACS

1. Vào **HACS → Kho lưu trữ tùy chỉnh**.
2. Thêm `https://github.com/marion001/VBot_Offline_Custom_Component`.
3. Chọn loại **Integration** và tải VBot Assistant.
4. Khởi động lại Home Assistant.
5. Vào **Cài đặt → Thiết bị & dịch vụ → Thêm tích hợp → VBot Assistant**.
6. Nhập MQTT Client Name và URL API của loa.
7. Sau khi hoàn tất các bước sẽ tự động có các thực thể entity id xuất hiện
8. Bạn có thể thêm nhiều thiết bị Loa VBot vào Home Assistant (HASS) bằng cách nhấn vào:
    - Cài đặt -> Thiết bị & Dịch vụ -> VBot Assistant MQTT -> Thêm Mục -> điền tên Client MQTT của loa VBot khác vào

URL API chấp nhận các dạng:

```text
192.168.1.20:5002
http://192.168.1.20:5002
https://vbot.example.com
```


       

## Thêm nhiều loa

Thêm một config entry cho mỗi loa. MQTT Client Name phải đúng với cấu hình của loa:

```text
VBot_Phong_Khach
VBot_Phong_Ngu
VBot_Nha_Bep
```

Không dùng chung MQTT Client Name cho nhiều loa.

## Media Player

Entity được tạo có dạng:

```text
media_player.media_player_vbot_phong_khach
```

Tên entity thực tế có thể khác nếu Home Assistant đã từng tạo entity trước đó. Hãy kiểm tra trong **Cài đặt → Thiết bị & dịch vụ → Thực thể**.

Các chức năng được hỗ trợ:

| Chức năng | Nhạc nội bộ | AirPlay | Bluetooth |
|---|---:|---:|---:|
| Play/Pause/Stop | Có | Theo backend | Theo backend |
| Volume | Có | Có | Có |
| Mute/Unmute | Có | Có | Có |
| Seek | Có | Không | Không |
| Next/Previous | Khi phát playlist | Không | Không |
| Metadata | Có | Nếu nguồn cung cấp | Nếu nguồn cung cấp |

Ví dụ thẻ Lovelace:

```yaml
type: media-control
entity: media_player.media_player_vbot_phong_khach
```

Ví dụ điều khiển bằng service:

```yaml
action:
  - service: media_player.media_play_pause
    target:
      entity_id: media_player.media_player_vbot_phong_khach
```

Tua tới giây thứ 90:

```yaml
action:
  - service: media_player.media_seek
    target:
      entity_id: media_player.media_player_vbot_phong_khach
    data:
      seek_position: 90
```

Đặt âm lượng 70%:

```yaml
action:
  - service: media_player.volume_set
    target:
      entity_id: media_player.media_player_vbot_phong_khach
    data:
      volume_level: 0.7
```

Mute loa:

```yaml
action:
  - service: media_player.volume_mute
    target:
      entity_id: media_player.media_player_vbot_phong_khach
    data:
      is_volume_muted: true
```

Phát URL:

```yaml
action:
  - service: media_player.play_media
    target:
      entity_id: media_player.media_player_vbot_phong_khach
    data:
      media_content_type: music
      media_content_id: "https://example.com/audio.mp3"
```

## TTS

### Service TTS

Service dùng chung cho mọi loa; `device_id` là MQTT Client Name của loa đích:

```yaml
service: tts_vbot_assistant.say
data:
  device_id: VBot_Phong_Khach
  message: "Xin chào, đây là thông báo từ Home Assistant"
```

Có thể dùng `text` thay cho `message`:

```yaml
service: tts_vbot_assistant.say
data:
  device_id: VBot_Phong_Ngu
  text: "Đã đến giờ đi ngủ"
```

Ví dụ automation thông báo cửa mở:

```yaml
alias: VBot thông báo cửa mở
trigger:
  - platform: state
    entity_id: binary_sensor.cua_chinh
    to: "on"
action:
  - service: tts_vbot_assistant.say
    data:
      device_id: VBot_Phong_Khach
      message: "Cửa chính đang mở"
mode: single
```

### Text và Button TTS

Nhập nội dung vào:

```text
text.<device>_vbot_tts
```

Sau đó nhấn:

```text
button.<device>_vbot_tts
```

## Conversation Agent

Component tạo một agent VBot cho mỗi config entry. Trong Assist Pipeline, chọn agent tương ứng với loa cần xử lý.

Hai chế độ:

- `chatbot`: chỉ trả văn bản về Home Assistant, không phát TTS và không chạy LED trên loa.
- `processing`: xử lý lệnh giống luồng chính của VBot, bao gồm điều khiển thiết bị/media; kết quả vẫn trả về Assist.

Chọn chế độ bằng entity:

```text
select.assist_tac_nhan_che_do_xu_ly_<device>
```

Luồng kết nối hiện dùng API:

```text
select.assist_tac_nhan_luong_xu_ly_<device> = api
```

Khi thay URL API trong Options, integration tự reload agent.

## Nhóm entity khác

- `number`: âm lượng và độ sáng LED.
- `switch`: microphone, conversation mode, media player, wake-up trong khi phát nhạc, nguồn YouTube/Zing/NhacCuaTui/Radio/Podcast/Local và các tùy chọn VBot khác.
- `select`: kiểu hiển thị log và chế độ Agent.
- `sensor`: phiên bản/ngày phát hành chương trình và giao diện.
- `button`: media, volume, playlist, báo chí, TTS, xử lý câu lệnh và nguồn hệ thống.
- `text`: nội dung TTS, câu lệnh xử lý, tên báo và URL nhạc.

## MQTT topics chính

```text
<device>/media_player/state
<device>/availability
<device>/tts/state
<device>/script/media_control/set
<device>/script/playlist_control/set
<device>/script/volume_control/set
<device>/script/vbot_tts/set
<device>/script/main_processing/set
<device>/number/volume/set
<device>/number/led_brightness/set
```

Topic trạng thái dùng retained message. Topic lệnh của component luôn dùng `retain=false` để không chạy lại lệnh cũ khi VBot kết nối lại.

`<device>/tts/state` lần lượt trả về `generating`, `playing`, `finished` hoặc
`error`. Media Player cũng cung cấp các thuộc tính `playlist_active`,
`playlist_index`, `playlist_total` và `playlist_loop`.

## Xử lý sự cố

Sau khi nâng cấp component, hãy khởi động lại Home Assistant. Nếu entity cũ
không nhận capability mới (seek/mute/next/previous), vào **Cài đặt → Thiết bị
& dịch vụ → Thực thể**, kiểm tra entity bị vô hiệu hóa hoặc xóa entity cũ rồi
để integration tạo lại.

### Entity Media Player unavailable

- Kiểm tra MQTT Broker và MQTT Client Name.
- Kiểm tra VBot đã bật MQTT.
- Kiểm tra topic `<device>/media_player/state` bằng MQTT Explorer.

### TTS không phát

- Kiểm tra `device_id` đúng MQTT Client Name.
- Kiểm tra topic `<device>/script/vbot_tts/set`.
- Kiểm tra TTS engine đang được bật trong VBot.
- Kiểm tra `sensor.trang_thai_tts_<device>`; trạng thái `error` có thuộc tính
  `error` mô tả nguyên nhân.

### Agent không phản hồi

- Mở URL API VBot từ máy Home Assistant.
- Kiểm tra port API, firewall và URL trong Options.
- Chọn luồng `api` và chế độ `chatbot` hoặc `processing`.

### Next/Previous không hoạt động

Hai nút chỉ hoạt động khi VBot đang phát playlist. Chúng không điều khiển danh sách phát trên điện thoại qua AirPlay/Bluetooth.

### Không tua được

Seek chỉ hỗ trợ Media Player nội bộ. Home Assistant gửi giây; component tự chuyển sang mili-giây cho VLC. WebUI VBot vẫn giữ định dạng mili-giây cũ.

## Liên kết

- VBot Offline: https://github.com/marion001/VBot_Offline
- Hỗ trợ: https://www.facebook.com/groups/1148385343358824


<img width="1911" height="915" alt="Image" src="https://github.com/user-attachments/assets/5ed4cfb8-6b05-428d-959c-328149373f60" />
<img width="1901" height="909" alt="Image" src="https://github.com/user-attachments/assets/b2437e4c-d41c-46b2-a094-a3d136001448" />
<img width="1887" height="901" alt="Image" src="https://github.com/user-attachments/assets/74429691-9bb3-49b1-b72d-ea136776c33d" />
<img width="1913" height="919" alt="Image" src="https://github.com/user-attachments/assets/3189100c-afe1-4fe7-81dd-d17a4a0df770" />