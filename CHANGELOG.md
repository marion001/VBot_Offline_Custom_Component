# Changelog

## 1.10.1 — 08-10-2026

- Cập nhật metadata mDNS khi URL không đổi, tránh reload cho metadata/timestamp.
- Capability theo snapshot MQTT/mDNS/Media API, loại bỏ capability cũ theo nguồn có thẩm quyền.
- Sửa duration/position audio dài: chỉ chuyển milliseconds khi field yêu cầu.
- Select nguồn phát ghi log và thuộc tính lý do backend từ chối, giữ trạng thái theo snapshot.
- Thêm tùy chọn timeout Assist 15–180 giây, timeout kết nối HTTP 5 giây.
- Bổ sung test hồi quy cho các thay đổi trên.


## 1.10.0 — 04-10-2026

- Sửa so sánh cập nhật: chuẩn hóa định dạng ngày, xét cả phiên bản khi cùng ngày phát hành, hiển thị riêng bản đang cài/bản GitHub và làm mới thông báo sau khi cập nhật thành công.
- Assist khi hết thời gian chờ nhắc kiểm tra trạng thái thiết bị trước khi gửi lại lệnh điều khiển, vì VBot có thể đã nhận lệnh.
- Sửa kiểm tra câu trả lời chọn thiết bị: tên không dấu dùng cùng cách chuẩn hóa với bộ tìm kiếm, vẫn kiểm tra số thiết bị để tránh chọn nhầm đích.
- Assist ở chế độ processing giữ mã phiên hội thoại và tiếp tục nghe khi VBot hỏi chọn thiết bị Home Assistant; câu trả lời áp dụng hành động bật/tắt đã lưu, kiểm tra lại quyền điều khiển và hết hạn sau 30 giây.
- Thêm Multiroom Audio vào select nguồn phát WebUI/MQTT: tiếp tục phiên hiện có tại loa, giữ nhóm và chỉ tạm dừng phát tại loa khi đổi nguồn.
- Chặn select chuyển nguồn khi loa chủ đang cấp âm thanh cho nhóm; từ chối chuyển nếu không xác định được vai trò Multiroom.
- Sửa kiểm tra dừng BlueALSA: bỏ qua tiến trình zombie, cho phép pgrep chờ 2 giây và trả về chi tiết lỗi/PID khi nhường ALSA thất bại.
- Giữ phiên AirPlay khi chuyển nguồn bằng disable ALSA/mute, chọn lại bằng enable ALSA/unmute; không gửi pause/play, callback đến muộn không thay thế nguồn được chọn.
- Thêm select Nguồn Phát Media (Local/VBot, Bluetooth, AirPlay) qua MQTT; lấy trạng thái từ snapshot thực tế và dùng chung xử lý chuyển nguồn với WebUI.
- Chuyển xử lý chuyển nguồn MQTT sang tác vụ nền; nhả quyền ALSA của AirPlay trước khi phát Bluetooth và hủy lệnh hàng đợi đã hết thời gian chờ.
- Sửa lỗi biến chưa khai báo khi tạo thông báo cập nhật; giữ thông báo cũ nếu kiểm tra cập nhật thất bại.
- Tách availability của lựa chọn Assist khỏi MQTT để không tự chuyển processing thành chatbot khi MQTT offline.
- Kiểm tra phản hồi Assist với success đúng kiểu boolean; bỏ qua snapshot select và số MQTT không hợp lệ.
- Sửa va chạm nhãn/ID trong select động; xử lý dữ liệu API khám phá thiết bị sai cấu trúc.
- Hủy tác vụ làm mới metadata đang chờ khi update entity bị gỡ/reload và xử lý timeout cập nhật.

- Khôi phục chế độ xử lý và luồng Assist sau restart/reload bằng RestoreEntity, lưu riêng lựa chọn để hỗ trợ cả khi MQTT unavailable.
- Chỉ khôi phục tùy chọn hợp lệ; cấu hình cũ không hợp lệ dùng chatbot/api.
- Bổ sung kiểm tra Assist: phản hồi văn bản, lỗi HTTP/xác thực/timeout, nhiều loa, setup rollback, unload/reload và khôi phục lựa chọn.

## 1.9.0

- Thêm Home Assistant Repairs cho MQTT Client ID trùng, API key bị từ chối và Media API không tương thích.
- Thêm binary sensor chuẩn cho kết nối MQTT, microphone và kết nối Bluetooth; mặc định tắt để không làm tăng entity ngoài ý muốn.
- Nhận danh sách capability từ mDNS, lưu theo config entry và bổ sung capability/media API version vào diagnostics.
- Liên kết availability coordinator trực tiếp với runtime của từng config entry.
- Tự khởi chạy Reauth khi WebUI Media API trả HTTP 401.
- Bổ sung kiểm thử contract cho Repairs, capability discovery và entity translations.
- Đồng bộ backend VBot: mDNS/MQTT capability contract, OTA status retained và tùy chọn backup trước cập nhật.
- Giữ Media state ở chu kỳ 1 giây; playlist state tối đa mỗi 2 giây; Multiroom mỗi 1 giây khi hoạt động, 5 giây khi rảnh; host sensor mỗi 5 giây. Cache playlist manifest theo `mtime`, cache danh sách nhóm Multiroom 10 giây và gom OTA status về một MQTT subscription mỗi thiết bị.

## 1.8.31

- Chặn MQTT Client ID trùng không phân biệt chữ hoa/chữ thường và hiển thị thông báo chỉ rõ thiết bị xung đột.
- Gom availability MQTT về một coordinator duy nhất cho mỗi thiết bị, giảm subscription và callback lặp lại.
- Hợp nhất kiểm tra cập nhật thủ công, định kỳ và update entity qua một metadata store dùng chung.
- Giữ nguyên quy ước VBot: release date hoặc version khác nhau đều được xem là có bản khác, kể cả downgrade.
- Chuyển timer kiểm tra cập nhật vào vòng đời entity để reload/unload dọn tài nguyên an toàn.
- Bổ sung kiểm thử identity, coordinator, cấu hình pytest/Ruff và workflow CI cho pytest, hassfest, HACS.

## 1.8.30

- Tương thích Home Assistant 2026.6+: Reconfigure/Reauth dùng
  `async_update_and_abort`; update listener thực hiện đúng một lần reload, tránh
  cơ chế double-reload đã bị Home Assistant deprecate.
- Update Entity coi bất kỳ khác biệt nào trong chuỗi `releaseDate - version` là
  bản cập nhật, đúng với quy ước phát hành của VBot.
- Gửi `VBot-API-Key` khi đọc `Version.json` local trong kiểm tra cập nhật thủ
  công/tự động, hoạt động cả khi API Auth WebUI được bật.
- Media Source tôn trọng bộ lọc loại media do Home Assistant truyền vào khi tìm
  kiếm; đồng bộ đầy đủ khóa dịch giữa `strings.json`, tiếng Việt và tiếng Anh.
- Loại các khóa `conversation` và `platforms` không thuộc schema manifest; các
  dependency và entity platform vẫn được nạp bởi lifecycle của integration.
- Nâng phiên bản Home Assistant tối thiểu trong HACS lên `2026.8.0`, tương ứng
  với API Media Browser Search mà custom đang sử dụng.
- Cảnh báo Media API cũ/thiếu capability chỉ ghi vào Home Assistant log ở mức
  warning, không còn tạo Persistent Notification trong giao diện.
- Thêm endpoint phiên bản/capabilities cho Media API WebUI.
- Tự kiểm tra tương thích theo từng VBot khi ConfigEntry được nạp, chạy nền để
  không làm chậm Home Assistant khi loa tắt hoặc mất mạng.
- Ghi cảnh báo log khi loa dùng Media API quá cũ, ví dụ
  `VBot_PhongNgu cần cập nhật Media API`.
- Đưa phiên bản, capabilities thiếu và trạng thái tương thích vào Diagnostics và
  System Health; lỗi mạng tạm thời không bị kết luận nhầm là phần mềm cũ.
- Cập nhật README đầy đủ cho Media Browser, cache/search, playlist play-all,
  API Auth, Reconfigure, Update Entity, MQTT availability và xử lý sự cố.

## 1.8.29

- Không còn che lỗi xác thực/phiên bản PHP ở thư mục Playlist thành
  `Không có mục nào`; hiển thị đúng lỗi WebUI hoặc yêu cầu cập nhật PHP.
- Thêm kiểm tra chặt phản hồi `Playlist_Manager` trước khi dựng Media Browser.

## 1.8.28

- Thêm mục `Phát toàn bộ` ở đầu mỗi thư mục playlist trong Media Browser.
- Gửi trực tiếp lệnh MQTT playlist có `playlist_id`, giữ nguyên chế độ phát, loop,
  Next/Previous và trạng thái playlist do VBot quản lý.

## 1.8.27

- Hiển thị kết quả tìm kiếm gần nhất từ cache WebUI ngay trong từng thư mục
  Zing MP3, YouTube, NhacCuaTui và Podcast.
- Các thư mục cache vẫn giữ ô tìm kiếm để thay thế danh sách bằng truy vấn mới.
- Lỗi đọc cache không làm hỏng Media Browser; ghi cảnh báo và hiển thị thư mục rỗng.

## 1.8.26

- Giữ tên bài hát, ảnh bìa và nguồn phát từ kết quả Media Browser xuyên suốt
  bước resolve và payload MQTT; không còn hiển thị hash/tên file URL làm tiêu đề.
- YouTube được gửi bằng URL chuẩn cho bộ resolve sẵn có của VBot, loại bỏ phụ
  thuộc endpoint PHP/SSH `GetLink_Youtube` gây HTTP 500.
- Nhạc Local ưu tiên metadata do Home Assistant gửi thay vì luôn dùng basename.

## 1.8.25

- Sửa lỗi Media Browser hiển thị `[object Object]` khi provider tìm kiếm trả lỗi.
- Chuẩn hóa lỗi lồng nhau từ YouTube/Zing/NhacCuaTui/Podcast thành nội dung dễ đọc,
  hiển thị trực tiếp trong kết quả và ghi log Home Assistant để chẩn đoán.

## 1.8.24

- Sửa Media Browser Local để hiển thị và phát đúng file thuộc
  `/home/pi/VBot_Offline/Media/Music_Local`, không đổi nhầm thành URL Home Assistant.
- Đồng bộ xác thực PHP media API với `api.auth`: khi tắt auth cho phép GET media,
  khi bật auth bắt buộc `VBot-API-Key`; các POST thay đổi dữ liệu vẫn giữ CSRF.
- Không còn che lỗi đăng nhập/API thành “không tìm thấy kết quả”; Media Browser trả
  rõ lỗi từng nguồn Zing MP3, YouTube, NhacCuaTui hoặc Podcast.
- Cho phép mở từng thư mục dịch vụ tìm kiếm để dùng ô search theo nguồn.

## 1.8.23

- Thêm Media Source `VBot` và Media Browser riêng trên Media Player.
- Hỗ trợ duyệt nhạc Local, nhiều Playlist và Radio từ dữ liệu WebUI.
- Hỗ trợ tìm kiếm Zing MP3, YouTube, NhacCuaTui và Podcast bằng chính PHP API
  của WebUI; link Zing/YouTube được resolve tại thời điểm phát.
- Cho phép Home Assistant xác thực PHP media API bằng header `VBot-API-Key`
  khi WebUI đang bật đăng nhập.

## 1.8.22

- Chuyển Reconfigure và Reauth sang helper chuẩn Home Assistant
  `async_update_reload_and_abort`, bảo đảm cập nhật ConfigEntry rồi reload integration.

## 1.8.21

- Hiển thị ngày phát hành và số phiên bản trong `/config/updates` theo dạng `releaseDate - version` cho cả chương trình VBot và WebUI.
- Subscribe thêm retained MQTT release date local để `installed_version` và `latest_version` có cùng định dạng, tránh báo cập nhật giả.

## 1.8.20

- Thêm Download diagnostics cho từng config entry, tự động che API key, password và token.
- Thêm System Health tổng hợp số VBot đã cấu hình, đã load và đang online.
- Diagnostics ghi nhận thời điểm availability thay đổi, lần gửi `state_sync` và số entity đăng ký.
- Phân loại các sensor kỹ thuật như MQTT, phiên bản, IP, Wi-Fi, mDNS và thời gian khởi động vào nhóm Diagnostic.

## 1.8.19

- Bổ sung cảm biến MQTT availability riêng cho Android/Phicomm client, đồng nhất với loa host và ESP32.
- Client nhận retained `online` sau reload/reconnect sẽ khôi phục đồng loạt availability cho toàn bộ control cùng thiết bị.

## 1.8.18

- Gom các lần ghi state khi MQTT availability thay đổi bằng scheduler của Home Assistant, giảm cảnh báo entity update chậm lúc reconnect.
- Dynamic playlist/multiroom select không còn sao chép toàn bộ bảng `items` vào state attributes; vẫn giữ `selected_id` phục vụ các button điều khiển.

## 1.8.17

- Đồng nhất kiểm tra cập nhật thủ công và tự động: button, công tắc và lịch 12 giờ đều refresh native update entity và trang `/config/updates`.
- Giữ persistent notification khi có phiên bản khác; kiểm tra thủ công vẫn thông báo cả trạng thái mới nhất hoặc thất bại.

## 1.8.16

- Button `VBot Check Updates` đồng thời refresh hai native update entity của chương trình VBot và WebUI.
- Khi phiên bản local và GitHub khác nhau, bản cập nhật xuất hiện trong trang Home Assistant `/config/updates` ngoài persistent notification.
- Xóa cache metadata GitHub khi người dùng kiểm tra thủ công để luôn nhận kết quả mới nhất.

## 1.8.15

- Sửa button `VBot Check Updates` trước đây khai báo command nhưng không thực thi khi bấm.
- Kiểm tra thủ công luôn phản hồi bằng persistent notification: có cập nhật, đang mới nhất hoặc không kiểm tra được.

## 1.8.14

- Theo quy ước phát hành VBot, coi `releaseDate` khác file local là có bản cập nhật, không phụ thuộc ngày lớn hơn hay nhỏ hơn.
- Khi thiếu ngày phát hành, coi số `version` khác nhau là có cập nhật.

## 1.8.13

- Chỉ thông báo cập nhật khi `releaseDate` trên GitHub thực sự mới hơn file local; không còn coi mọi ngày khác nhau là bản cập nhật.
- Dùng số `version` làm phương án so sánh dự phòng khi ngày phát hành không đúng định dạng hỗ trợ.

## 1.8.12

- Không còn dùng trạng thái phát media `unavailable` để đánh dấu toàn bộ thiết bị MQTT offline; chỉ topic LWT/availability và kết nối broker được quyền thay đổi availability chung.
- Khai báo Home Assistant tối thiểu `2024.5.0`, phù hợp với việc integration sử dụng `ConfigEntry.runtime_data`.
- Không khai báo `aiohttp` là dependency cài ngoài vì thư viện này đã thuộc Home Assistant Core; bổ sung `integration_type` và `iot_class` cho manifest.

## 1.8.11

- Sửa lỗi `TypeError: 'functools.partial' object can't be awaited` khi thêm entity trên các bản Home Assistant mà `mqtt.async_on_subscribe_done()` trả về unsubscribe callback trực tiếp.

## 1.8.10

- Cho mọi entity điều khiển đọc trực tiếp availability dùng chung theo `device_id`, loại bỏ trạng thái `_attr_available` cũ còn sót lại sau MQTT reconnect.

## 1.8.9

- Sửa callback MQTT broker kết nối thành công vô tình đặt toàn bộ entity về `unavailable`.
- Đồng bộ trạng thái online đã nhận cho các entity được tạo muộn hơn cảm biến availability khi reload integration.

## 1.8.8

- Đồng bộ availability của toàn bộ entity theo cả kết nối MQTT Home Assistant và retained/LWT của từng VBot.
- Giữ entity ở trạng thái unavailable cho đến khi broker xác nhận subscription và VBot phản hồi online.
- Chủ động gửi `state_sync` sau khi reload integration, Home Assistant hoặc MQTT broker kết nối lại.
- Không kiểm tra cập nhật chương trình/WebUI khi thiết bị chưa online; tự kiểm tra lại khi kết nối phục hồi.
- Chống gửi trùng lệnh đồng bộ khi nhiều entity của cùng thiết bị được khởi tạo đồng thời.

## 1.8.7

- Xác minh API key, loại thiết bị và MQTT Client ID trước khi mDNS tự đổi URL API.
- Nâng Config Entry lên phiên bản 4; URL/API key chỉ lưu trong `data`, các tùy chọn hành vi chỉ lưu trong `options`.
- Conversation Agent tìm các select Assist bằng `unique_id`, không phụ thuộc entity ID do người dùng có thể đổi.
- Chuẩn hóa tiêu đề media từ metadata hoặc đường dẫn URL đã giải mã và loại bỏ query string.
- Tách Reconfigure dùng cho URL/API key và Options dùng cho tự cập nhật URL qua mDNS.

## 1.8.6

- Treat an empty or coordinator-only Home Assistant join request as leaving Multiroom and returning to local playback.

## 1.8.5

- Reject duplicate MQTT Client IDs instead of mapping commands to the wrong speaker.
- Propagate the complete group membership from coordinator to every receiver, including after adding or removing speakers.
- Map Home Assistant `group_members` with MQTT Client IDs while retaining hardware IDs for the backend.

## 1.8.4

- Tự thêm media player coordinator vào stream khi ghép nhóm từ Home Assistant.
- Báo trạng thái Multiroom đang kết nối cho cả coordinator và receiver.
- Tương thích ánh xạ MQTT client ID sang hardware ID Multiroom ở backend.

## 1.8.3

- Chuyển callback sự kiện MQTT về event loop trước khi truy cập registry và event bus.
- Thay API `async_get_device` đã deprecated bằng lookup theo identifier và config entry.

## 1.8.2

- Huỷ đúng tác vụ tự kiểm tra cập nhật khi reload hoặc gỡ config entry.
- Chỉ gỡ conversation agent sau khi toàn bộ platform unload thành công.
- Dùng chung cache metadata GitHub và giới hạn polling cập nhật còn 12 giờ.
- Giảm tải bridge Multiroom bằng cache trạng thái ngắn 5 giây.
- Chỉ cung cấp event/device trigger cho loa chủ đang hỗ trợ event contract.
- Bổ sung đầy đủ thông báo lỗi discovery cho strings và bản dịch tiếng Việt.

## 1.8.1

- Dịch vụ `vbot_assistant.say` hỗ trợ target selector để chọn một hoặc nhiều
  VBot theo Device hoặc Media Player entity.
- Tự phân biệt Home Assistant device ID với MQTT client ID cũ và giữ tương thích
  các automation hiện có.
- Xác minh target thuộc integration VBot, loại bỏ target trùng và báo lỗi dịch
  vụ rõ ràng khi thiếu nội dung hoặc thiết bị.

## 1.8.0

- Thêm event contract MQTT `{device}/event` với UUID, timestamp UTC, data và
  chính sách không retain.
- Thêm Device Trigger cho Wake Word, STT, command, TTS, Bluetooth, Multiroom và
  trạng thái Media trong Automation UI.
- Chống xử lý event trùng bằng bộ nhớ tối đa 256 event ID cho từng Config Entry.
- Chỉ phát event chuyển trạng thái Media/Bluetooth/Multiroom, không phát lặp theo
  chu kỳ snapshot.

## 1.7.0

- Thêm native Multiroom grouping bằng `media_player.join` và
  `media_player.unjoin` cho loa chủ VBot.
- Ánh xạ entity ID qua Entity Registry sang MQTT client ID; không phụ thuộc tên
  hiển thị hoặc entity ID do người dùng đổi.
- Mở rộng MQTT Multiroom với join/add/remove/sync speakers và công bố danh sách
  speaker cùng vai trò coordinator trong retained state.
- Tự tạo nhóm tạm riêng theo coordinator khi Home Assistant thực hiện join.
- Mọi command Multiroom đều không retain để tránh phát lại lệnh cũ.

## 1.6.1

- Thêm Reconfigure Flow để đổi URL API, API key và chế độ cập nhật URL qua mDNS
  mà không xóa Config Entry.
- Thêm Reauth Flow để thay API key và tự khởi chạy khi Conversation API trả 401.
- Kiểm tra thiết bị, loại profile và MQTT client ID trước khi lưu cấu hình mới.
- Dùng `async_update_and_abort` để update listener chỉ reload entry một lần trên
  Home Assistant 2026.6 trở lên.

## 1.6.0

- Thêm hai Update Entity chuẩn của Home Assistant cho chương trình và giao diện
  VBot trên profile Host.
- Hiển thị phiên bản đang cài qua MQTT, phiên bản mới nhất và ghi chú phát hành
  từ repository VBot.
- Cho phép cài đặt trực tiếp bằng action `update.install`; lệnh MQTT cập nhật
  không retain để không bị phát lại khi thiết bị kết nối lại.
- Giữ các button cập nhật cũ để tương thích với dashboard và automation hiện có.

## 1.5.1

- Thêm base entity dùng chung cho thông tin Device Registry của các entity MQTT.
- Chuyển switch MQTT sang `VBotSwitchEntityDescription`; giữ nguyên tên, topic,
  payload, unique ID và trạng thái optimistic hiện có.
- Giữ lớp chuyển đổi cấu hình cũ để các profile Host, Android và ESP32 sử dụng
  cùng một định nghĩa switch mà không làm thay đổi entity của người dùng.

## 1.5.0

- Thêm `VBotRuntimeData` độc lập cho từng Config Entry, chứa cấu hình thiết bị và
  API client riêng.
- Conversation Agent sử dụng API client của runtime thay vì tự đọc lại dữ liệu
  cấu hình và tạo HTTP request riêng.
- Loại bỏ việc lưu dữ liệu Config Entry vào `hass.data`; giữ nguyên unique ID và
  entity ID hiện có.

## 1.4.5

- Cô lập URL kiểm tra cập nhật cho từng Config Entry, tránh thiết bị này sử dụng
  nhầm địa chỉ của thiết bị khác khi kiểm tra đồng thời.
- Quản lý lịch tự động kiểm tra cập nhật theo `entry_id`; giữ nguyên entity ID và
  hành vi điều khiển hiện có.

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
