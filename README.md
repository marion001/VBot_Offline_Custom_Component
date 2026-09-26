# VBot Assistant cho Home Assistant

Custom component kết nối một hoặc nhiều loa VBot với Home Assistant qua MQTT và API.

Phiên bản hiện tại: `1.9.0`.

Yêu cầu Home Assistant **2026.8.0 trở lên** vì Media Browser Search sử dụng API
tìm kiếm media mới của Home Assistant.

## Chức năng

- Media Player: play, pause, resume, stop, next, previous, seek, volume và mute.
- Đồng bộ tên bài, nguồn phát, nghệ sĩ, album, ảnh bìa, thời lượng và trạng thái online.
- Điều khiển nhạc nội bộ, playlist, AirPlay và Bluetooth theo khả năng của từng nguồn.
- Media Browser riêng cho từng VBot: duyệt nhạc local, playlist, radio và tìm
  kiếm Zing MP3, YouTube, NhacCuaTui, Podcast qua API WebUI hiện có.
- Phát TTS bằng Text + Button hoặc service `vbot_assistant.say`.
- Dùng VBot làm Conversation Agent cho Home Assistant Assist.
- Điều khiển các switch cấu hình VBot, âm lượng, LED và nguồn nội dung.
- Hiển thị phiên bản chương trình/giao diện VBot và kiểm tra cập nhật.
- Hiển thị Update Entity trong `/config/updates` với ngày phát hành và phiên bản.
- Theo dõi MQTT availability; entity điều khiển tự chuyển `unavailable` khi loa
  hoặc broker mất kết nối và phục hồi sau khi đồng bộ lại trạng thái.
- Kiểm tra phiên bản/capabilities Media API riêng cho từng loa và ghi cảnh báo
  vào Home Assistant log khi thiết bị cần cập nhật.
- Hỗ trợ nhiều loa; mỗi loa được phân biệt bằng MQTT Client Name.

## Yêu cầu

1. VBot và Home Assistant truy cập được cùng MQTT Broker.
2. MQTT Broker đã được cấu hình và bật trong `Config.json` của từng loa.
3. Mỗi loa phải có `mqtt_client_name` riêng, ví dụ `VBot_Phong_Khach`.
4. API VBot phải truy cập được từ Home Assistant, ví dụ `192.168.1.20:5002`.
5. Muốn dùng Media Browser, loa chủ phải có bản
   `html/includes/php_ajax/Media_Player_Search.php` tương thích Media API v2.
6. Nếu bật `api.auth.active`, API key trong Config Entry phải trùng với
   `api.auth.api_key` của `Config.json` trên đúng loa đó.

## Loại thiết bị và URL API

Khi thêm thủ công, chọn đúng loại thiết bị. Có thể nhập URL có hoặc không có
`http://` và có hoặc không có dấu `/` cuối:

| Loại thiết bị | Ví dụ nhập | URL được sử dụng |
|---|---|---|
| Loa chủ VBot | `192.168.1.10` | `http://192.168.1.10:5002` |
| Phicomm R1 Client | `192.168.1.20` | `http://192.168.1.20:8081` |
| ESP32/ESP32-S3 Client | `192.168.1.30` | `http://192.168.1.30` |

Nếu đã nhập port riêng, integration giữ nguyên port đó. ESP32 mặc định dùng
HTTP cổng 80 nên không tự thêm port.

Thiết bị thêm thủ công mặc định giữ URL cố định. Thiết bị thêm bằng mDNS mặc
định bật **Tự động cập nhật URL API qua mDNS**. Có thể thay đổi chế độ này
trong phần **Cấu hình** của Config Entry.

Các entity thuộc nhóm chẩn đoán:

- `URL API Hiện Tại`
- `Nguồn URL API`
- `Lần Cập Nhật URL Qua mDNS`

Khi mDNS phát hiện cùng `device_id` ở IP mới, integration cập nhật entry hiện
có và reload các entity; không tạo thêm thiết bị trùng. Trước khi đổi URL,
integration gọi API địa chỉ mới để xác thực API key, loại thiết bị và
`mqtt_client_name`. Nếu xác thực thất bại, URL cũ được giữ nguyên.

Thông tin kết nối được thay đổi bằng **Reconfigure/Cấu hình lại**:

- URL API/IP/hostname.
- API key.
- Tự động cập nhật URL qua mDNS.

Options chỉ lưu tùy chọn hành vi, không lưu URL hoặc API key. Khi lưu
Reconfigure thành công, Home Assistant cập nhật Config Entry và reload
integration mà không làm mất thiết bị/entity hiện có.

## Cài đặt bằng HACS

1. Vào **HACS → Kho lưu trữ tùy chỉnh**.
2. Thêm `https://github.com/marion001/VBot_Offline_Custom_Component`.
3. Chọn loại **Integration** và tải VBot Assistant.
4. Khởi động lại Home Assistant.
5. Vào **Cài đặt → Thiết bị & dịch vụ → Thêm tích hợp → VBot Assistant**.
6. Nhập MQTT Client Name và URL API của loa.

URL API chấp nhận các dạng:

```text
192.168.1.20:5002
http://192.168.1.20:5002
https://vbot.example.com
```

Khi nâng cấp từ phiên bản cũ, Config Entry được migration tự động lên schema
version 4. Entry cũ được giữ ở chế độ URL thủ công để tránh thay đổi địa chỉ
ngoài ý muốn; URL/API key được chuyển về `ConfigEntry.data`, còn tùy chọn hành
vi nằm trong `ConfigEntry.options`. Không cần xóa và thêm lại integration.

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

## Media Browser và Media Source

Home Assistant cung cấp Media Source tên **VBot**. Mở:

```text
Media → VBot → <MQTT Client Name>
```

Cấu trúc trên mỗi loa chủ:

```text
VBot_Phong_Khach
├── Nhạc Local
├── Playlist
│   ├── Mặc định
│   └── <các playlist khác>
├── Radio
├── Zing MP3
├── YouTube
├── NhacCuaTui
└── Podcast
```

### Nhạc Local

Thư mục **Nhạc Local** đọc các file âm thanh từ:

```text
/home/pi/VBot_Offline/Media/Music_Local
```

Đường dẫn được giữ là đường dẫn local của VBot, không bị đổi thành URL của
Home Assistant. Tên bài, ảnh bìa và nguồn phát được gửi cùng payload MQTT.

### Playlist

Mỗi playlist hiển thị các bài để phát riêng lẻ. Mục đầu tiên là:

```text
▶ Phát toàn bộ — <tên playlist>
```

Lệnh phát toàn bộ dùng `playlist_id` native của VBot nên tiếp tục hỗ trợ chế
độ tuần tự/ngẫu nhiên/lặp một bài, loop, Next/Previous và đồng bộ trạng thái.

### Tìm kiếm và cache

Zing MP3, YouTube, NhacCuaTui và Podcast có ô tìm kiếm riêng. WebUI ghi kết
quả gần nhất vào cache; khi mở lại thư mục nguồn, Home Assistant hiển thị cache
trước đó mà không cần tìm lại:

| Nguồn | Cache WebUI |
|---|---|
| Zing MP3 | `html/includes/cache/ZingMP3.json` |
| YouTube | `html/includes/cache/Youtube.json` |
| NhacCuaTui | `html/includes/cache/NhacCuaTui.json` |
| Podcast | `html/includes/cache/PodCast.json` |

Zing MP3 được resolve lại URL stream khi phát. YouTube gửi URL video chuẩn cho
bộ resolver sẵn có của VBot, không phụ thuộc PHP/SSH `GetLink_Youtube`. Metadata
từ kết quả tìm kiếm được giữ xuyên suốt nên tên bài không biến thành hash hoặc
basename của URL.

### Chọn VBot làm thiết bị phát

Trong Media Browser, chọn bài rồi chọn entity Media Player của VBot, ví dụ:

```text
Media Player (VBot_Phong_Khach)
```

VBot cũng phát được URL/Media Source khác của Home Assistant nếu loa truy cập
được URL đã resolve. Không dùng `localhost` hoặc `127.0.0.1` làm Home Assistant
internal URL; hãy dùng IP/hostname mà VBot truy cập được.

### API key và đăng nhập WebUI

Đăng nhập WebUI và API Auth là hai lớp riêng:

| Login WebUI | API Auth | Media Browser |
|---|---:|---|
| Tắt | Tắt | Hoạt động không cần key |
| Bật | Tắt | GET media vẫn hoạt động |
| Tắt | Bật | Cần đúng `VBot-API-Key` |
| Bật | Bật | Cần đúng `VBot-API-Key` |

Các GET duyệt/tìm kiếm media tuân theo `api.auth`. Các POST thay đổi playlist
vẫn được bảo vệ bằng đăng nhập/CSRF.

### Media API version và cảnh báo tương thích

Custom kiểm tra nền endpoint:

```text
/includes/php_ajax/Media_Player_Search.php?Media_Source_Health=1
```

Media API v2 quảng bá các capability:

```text
local, playlist, playlist_play_all, radio,
search, cache, youtube_direct
```

Nếu một loa dùng PHP cũ hoặc thiếu capability, Home Assistant ghi cảnh báo
trong log, ví dụ:

```text
VBot_PhongNgu cần cập nhật Media API
```

Khi loa tương thích trở lại, custom không ghi thêm cảnh báo. Loa offline/mất
mạng tạm thời không bị kết luận nhầm là cần cập nhật.
Kết quả kiểm tra cũng có trong Download Diagnostics và System Health.

### Cập nhật PHP Media API trên từng loa

Chép file mới vào đúng từng loa chủ:

```text
/home/pi/VBot_Offline/html/includes/php_ajax/Media_Player_Search.php
```

Sau đó:

```bash
sudo systemctl restart apache2
```

Kiểm tra API Auth tắt:

```bash
curl -sS \
  'http://127.0.0.1/includes/php_ajax/Media_Player_Search.php?Media_Source_Health=1'
```

Nếu API Auth bật:

```bash
read -rsp 'VBot API key: ' VBOT_MEDIA_KEY
curl -sS \
  -H "VBot-API-Key: $VBOT_MEDIA_KEY" \
  'http://127.0.0.1/includes/php_ajax/Media_Player_Search.php?Media_Source_Health=1'
unset VBOT_MEDIA_KEY
```

Mỗi loa chủ phải được cập nhật riêng; cập nhật `VBot_DEV` không tự cập nhật
`VBot_PhongNgu`.

## Cập nhật chương trình và WebUI

Mỗi loa chủ có hai Update Entity native trong:

```text
Cài đặt → Hệ thống → Cập nhật
```

- `Cập Nhật Chương Trình VBot` đọc `Version.json`.
- `Cập Nhật Giao Diện VBot` đọc `html/Version.json`.

Ngày phát hành và phiên bản hiển thị cùng nhau:

```text
20/09/2026 - 1.3.1
```

Custom subscribe retained MQTT cho cả `version` và `releaseDate` của bản đang
cài, đồng thời đọc file tương ứng trên GitHub cho bản mới nhất. Nếu
`releaseDate` khác nhau thì được coi là có bản mới; khi thiếu ngày, `version`
được dùng làm phương án dự phòng.

Các cách kiểm tra:

- Nhấn button `VBot Check Updates` để kiểm tra ngay.
- Bật switch `Tự động kiểm tra cập nhật VBot` để kiểm tra định kỳ.
- Xem trực tiếp hai Update Entity trong `/config/updates`.

Khi thiết bị offline, custom bỏ qua kiểm tra cập nhật để tránh thông báo sai.
Metadata GitHub được cache dùng chung và kiểm tra lại khi thiết bị online trở
lại hoặc người dùng yêu cầu kiểm tra thủ công.

## MQTT availability và đồng bộ trạng thái

Mỗi VBot publish retained availability:

```text
<device>/availability = online | offline
```

Khi nhận `offline` hoặc Home Assistant mất kết nối MQTT, các entity điều khiển
chuyển sang `unavailable`. Việc này ngăn người dùng gửi button/switch command
tới loa không hoạt động. Khi kết nối lại:

1. VBot publish `online`.
2. Home Assistant gửi yêu cầu `state_sync`.
3. VBot publish lại toàn bộ retained state.
4. Entity rời trạng thái `unavailable` sau khi có availability/state hợp lệ.

Khi reload integration, custom xóa trạng thái availability cũ trong bộ nhớ và
chờ retained `online`, tránh hiển thị online giả từ phiên runtime trước.

Nếu availability đã online nhưng entity vẫn unavailable:

- Kiểm tra log `Đã đồng bộ lại toàn bộ trạng thái lên Home Assistant` trên VBot.
- Kiểm tra retained topic bằng MQTT Explorer.
- Kiểm tra broker có ACK và Home Assistant đã subscribe lại sau restart.
- Không publish command với `retain=true`; custom luôn dùng `retain=false`.

## TTS

### Service TTS

Trong Automation UI, chọn trực tiếp một hoặc nhiều thiết bị VBot ở mục tiêu.
Ví dụ YAML dùng target Device của Home Assistant:

```yaml
action: vbot_assistant.say
target:
  device_id:
    - 0123456789abcdef0123456789abcdef
data:
  message: "Xin chào, đây là thông báo từ Home Assistant"
```

Cũng có thể target Media Player entity:

```yaml
action: vbot_assistant.say
target:
  entity_id:
    - media_player.media_player_vbot_phong_khach
    - media_player.media_player_vbot_phong_ngu
data:
  message: "Thông báo phát trên hai loa"
```

Automation cũ dùng `device_id` là MQTT Client Name vẫn được hỗ trợ:

```yaml
action: vbot_assistant.say
data:
  device_id: VBot_Phong_Khach
  message: "Xin chào, đây là thông báo từ Home Assistant"
```

Có thể dùng `text` thay cho `message`:

```yaml
action: vbot_assistant.say
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
  - action: vbot_assistant.say
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

Khi thay URL API bằng Reconfigure, integration tự reload agent.

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
- Kiểm tra port API, firewall và URL trong Reconfigure.
- Chọn luồng `api` và chế độ `chatbot` hoặc `processing`.

### Báo trùng MQTT Client ID

Từ `1.8.31`, MQTT Client ID được kiểm tra không phân biệt chữ hoa/chữ thường.
Ví dụ `VBot_LivingRoom` và `vbot_livingroom` được xem là cùng một ID để tránh
trùng `unique_id` của entity. Home Assistant sẽ chặn entry mới và tạo thông báo
chỉ rõ thiết bị đã cấu hình đang xung đột; hãy đổi Client ID trên một thiết bị.

### Repairs và binary sensor

Phiên bản `1.9.0` đưa các lỗi cần người dùng xử lý vào mục **Sửa chữa** của Home
Assistant: Client ID trùng, API key bị từ chối và Media API WebUI quá cũ. Component
cũng cung cấp binary sensor chuẩn cho MQTT, microphone và Bluetooth. Các binary
sensor này mặc định tắt; bật chúng trong trang thiết bị nếu cần automation.

Backend VBot cùng phiên bản contract sẽ quảng bá capability qua mDNS và MQTT,
gửi trạng thái OTA tại
`<client_id>/update/state`, và hỗ trợ tùy chọn backup của Update Entity.

Media state giữ chu kỳ 1 giây. Playlist state tối đa mỗi 2 giây; Multiroom cập
nhật mỗi 1 giây khi hoạt động và mỗi 5 giây khi rảnh; host sensor tối đa mỗi
5 giây. Danh sách nhóm Multiroom được cache 10 giây. Playlist manifest được
cache một bản trong RAM và chỉ đọc lại khi file đổi
`mtime`. Cache không chứa nhạc hoặc ảnh bìa và không tích lũy phiên bản cũ.

### Media Browser yêu cầu đăng nhập WebUI

- Xác nhận đúng loa trong thông báo/log; Media Browser toàn cục có thể liệt kê
  nhiều VBot với phiên bản PHP khác nhau.
- Cập nhật `Media_Player_Search.php` trên chính loa báo lỗi và restart Apache.
- Nếu `api.auth.active=true`, Reconfigure Config Entry bằng đúng API key.
- Thử endpoint `Media_Source_Health=1` bằng `curl` như hướng dẫn ở trên.

### Playlist báo “Không có mục nào”

- Kiểm tra `Playlist_Manager=1` có trả `success=true` và mảng `playlists`.
- Custom từ `1.8.29` không còn che lỗi đăng nhập/PHP cũ thành thư mục rỗng.
- Kiểm tra file `html/includes/cache/PlayLists.json` và thư mục
  `html/includes/cache/playlists/` trên đúng loa.

### Tìm kiếm báo `[object Object]`

Nâng cấp custom từ `1.8.25` trở lên. Lỗi provider được chuyển thành văn bản và
ghi vào log `custom_components.vbot_assistant.media_source`. Với YouTube, kiểm
tra YouTube Data API v3, quota và giới hạn của Google API key.

### Tên bài hát hiển thị hash hoặc tên file

Nâng cấp custom `1.8.26` trở lên và cập nhật `Api.py`, `Api_MQTT.py` tương ứng
trên VBot. Các bản mới giữ title/artist/cover/source từ Media Browser qua MQTT.

### Cache nguồn trực tuyến không hiển thị

- Tìm kiếm ít nhất một lần để WebUI tạo/cập nhật cache.
- Kiểm tra quyền đọc các file cache Zing/YouTube/NhacCuaTui/Podcast.
- Kiểm tra log Media Source; lỗi xác thực không còn được coi là cache rỗng.

### Next/Previous không hoạt động

Hai nút chỉ hoạt động khi VBot đang phát playlist. Chúng không điều khiển danh sách phát trên điện thoại qua AirPlay/Bluetooth.

### Không tua được

Seek chỉ hỗ trợ Media Player nội bộ. Home Assistant gửi giây; component tự chuyển sang mili-giây cho VLC. WebUI VBot vẫn giữ định dạng mili-giây cũ.

## Liên kết

- VBot Offline: https://github.com/marion001/VBot_Offline
- Hỗ trợ: https://www.facebook.com/groups/1148385343358824
