/* VBot Ultimate Card. No CDN, no MQTT credentials, no extra polling connection. */
(() => {
  'use strict';
  const DOMAIN='vbot_assistant';
  const EQ=[['bass_db','100 Hz','Bass'],['low_mid_db','250 Hz','Low Mid'],['mid_db','630 Hz','Mid'],
    ['high_mid_db','1,6 kHz','Presence'],['treble_db','4 kHz','Treble'],['air_db','10 kHz','Air']];
  const offline=s=>!s||s.state==='unavailable'||(s.state==='unknown'&&!['button','input_button','select'].includes(domain(s.entity_id||'')));
  const domain=id=>id.split('.')[0];
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function discover(entities,devices,states){
    const ids=new Set(devices.filter(d=>(d.identifiers||[]).some(pair=>pair[0]===DOMAIN)).map(d=>d.id));
    entities.filter(e=>e.platform===DOMAIN&&e.device_id).forEach(e=>ids.add(e.device_id));
    return [...ids].map(id=>{
      const device=devices.find(d=>d.id===id);
      const rows=entities.filter(e=>e.device_id===id&&e.platform===DOMAIN&&!e.disabled_by&&!e.hidden_by&&states[e.entity_id]);
      return {id,name:device?.name_by_user||device?.name||id,entities:rows};
    }).filter(d=>d.entities.length).sort((a,b)=>a.name.localeCompare(b.name));
  }
  class VBotUltimateCard extends HTMLElement {
    constructor(){
      super();this.attachShadow({mode:'open'});this._tab='media';this._registry=null;this._loading=false;
      this._busy=new Set();this._signature='';this._generation=0;
      this._catalog=null;this._requestSeq=0;this._clock=null;
      this._playlistDrafts=new Map();this._ttsDrafts=new Map();this._composing=new Set();
      this._roomDrafts=new Map();
      this._btOperations=new Map();
      this._foldOpen={playlist:false,tts:false,library:false,'status-network':true,'status-audio':false,'status-system':false};
      this._mediaHeights=new Map();this._scrollPositions=new Map();
      this._scrollUntil=0;this._renderPending=false;this._scrollTimer=null;
      this._scrollActivity=()=>{
        this._scrollUntil=performance.now()+600;
        clearTimeout(this._scrollTimer);
        this._scrollTimer=setTimeout(()=>{
          this._scrollTimer=null;this._scrollUntil=0;
          if(this._renderPending){this._renderPending=false;this._queue();}
        },620);
      };
      this.shadowRoot.addEventListener('scroll',this._scrollActivity,{capture:true,passive:true});
      this._visibility=()=>{this._scheduleClock();this._updateProgress();};
      this.shadowRoot.addEventListener('click',e=>this._click(e));
      this.shadowRoot.addEventListener('change',e=>this._change(e));
      this.shadowRoot.addEventListener('input',e=>{
        const target=e.target;
        if(target.hasAttribute('data-search-query')&&this._catalog)this._catalog.query=target.value;
        if(target.hasAttribute('data-tts-draft'))this._ttsDrafts.set(this._selected,target.value);
        if(target.hasAttribute('data-room-volume')){const out=target.parentElement.querySelector('output');if(out)out.textContent=target.value+'%';return;}
        if(target.type==='range'){
          if(target.dataset.kind==='seek'){
            const out=this.shadowRoot.querySelector(`[data-elapsed="${CSS.escape(target.dataset.entity)}"]`);
            if(out)out.textContent=this._time(Number(target.value));return;
          }
          const out=this.shadowRoot.querySelector(`[data-value="${CSS.escape(target.dataset.entity)}"]`);
          if(out)out.textContent=target.value+(target.dataset.unit?' '+target.dataset.unit:'');
        }
      });
      this.shadowRoot.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target.hasAttribute('data-search-query')){e.preventDefault();e.target.blur();this._search();}});
      this.shadowRoot.addEventListener('error',e=>{if(e.target.tagName==='IMG')e.target.hidden=true;},true);
      this.shadowRoot.addEventListener('toggle',e=>{
        if(e.target.hasAttribute('data-media-extras'))this._extrasOpen=e.target.open;
        if(e.target.dataset.fold)this._foldOpen[e.target.dataset.fold]=e.target.open;
      },true);
      this.shadowRoot.addEventListener('focusout',()=>setTimeout(()=>this._queue(),0));
    }
    setConfig(config){
      if(config.device_id!==undefined&&typeof config.device_id!=='string')throw Error('device_id phải là chuỗi');
      if(config.entities!==undefined&&(!Array.isArray(config.entities)||config.entities.some(e=>typeof e!=='string')))throw Error('entities phải là danh sách entity_id');
      const previous=this._config;
      this._config={title:'VBot Ultimate',...config};
      if(!previous||(previous.device_id||'')!==(config.device_id||'')){this._selectDevice(config.device_id||null,false);this._restoredKey=null;}
      this._restoreSelection();
      this._signature='';this._queue();
    }
    set hass(value){
      const changed=this._entitiesRef!==value.entities||this._devicesRef!==value.devices;
      this._hass=value;this._entitiesRef=value.entities;this._devicesRef=value.devices;
      this._restoreSelection();
      if(!this._registryAttempted||changed)this._loadRegistry();
      this._queue();
    }
    connectedCallback(){
      document.addEventListener('visibilitychange',this._visibility);this._queue();this._scheduleClock();
      for(const type of ['wheel','touchmove','scroll'])document.addEventListener(type,this._scrollActivity,{capture:true,passive:true});
      if(window.ResizeObserver){this._resizeObserver??=new ResizeObserver(()=>this._measureMedia());this._resizeObserver.observe(this);}
    }
    disconnectedCallback(){
      if(this._frame)cancelAnimationFrame(this._frame);this._frame=null;
      clearTimeout(this._clock);this._clock=null;clearTimeout(this._scrollTimer);this._scrollTimer=null;this._scrollUntil=0;
      this._resizeObserver?.disconnect();document.removeEventListener('visibilitychange',this._visibility);
      for(const type of ['wheel','touchmove','scroll'])document.removeEventListener(type,this._scrollActivity,true);
    }
    getCardSize(){return 9;}
    getGridOptions(){return {columns:12,rows:'auto',min_columns:6};}
    static getStubConfig(){return {type:'custom:vbot-ultimate-card',title:'VBot Ultimate'};}
    static get version(){return '1.14.4';}
    static getConfigElement(){return document.createElement('vbot-ultimate-card-editor');}
    async _loadRegistry(){
      if(this._loading||!this._hass)return;
      this._loading=true;this._registryAttempted=true;
      try{
        const [entities,devices]=await Promise.all([
          this._hass.callWS({type:'config/entity_registry/list'}),this._hass.callWS({type:'config/device_registry/list'})]);
        this._registry={entities,devices};this._registryError='';
      }catch(error){this._registryError=error.message||'Không đọc được registry. Kiểm tra quyền tài khoản Home Assistant.';}
      finally{this._loading=false;this._signature='';this._queue();}
    }
    _queue(){
      if(!this.isConnected||this._frame)return;
      this._frame=requestAnimationFrame(()=>{this._frame=null;this._render();});
    }
    _rows(){
      if(!this._device)return [];
      return this._device.entities.filter(e=>!this._config.entities||this._config.entities.includes(e.entity_id));
    }
    _storageKey(){
      return 'vbot-ultimate:device:'+JSON.stringify([location.pathname,this._hass?.user?.id||'',this._config?.storage_key||[this._config?.title,this._config?.device_id||'',this._config?.entities||null]]);
    }
    _restoreSelection(){
      if(!this._config||!this._hass)return;
      const key=this._storageKey();if(this._restoredKey===key)return;this._restoredKey=key;
      try{const saved=localStorage.getItem(key);if(saved&&saved.length<=256)this._selectDevice(saved,false);}catch(_){/* Browser storage can be disabled. */}
    }
    _selectDevice(id,persist=true){
      if(id!==this._selected){this._selected=id;this._device=null;this._generation++;this._requestSeq++;this._catalog=null;this._error='';this._signature='';}
      if(persist&&id){try{localStorage.setItem(this._storageKey(),id);}catch(_){}}
    }
    _findEntity(type,suffix){return this._rows().find(e=>domain(e.entity_id)===type&&e.unique_id?.endsWith(suffix));}
    _eq(key){return this._rows().find(e=>e.unique_id?.endsWith('_equalizer_'+key));}
    _name(row){return this._hass.formatEntityName?.(this._hass.states[row.entity_id])||this._hass.states[row.entity_id]?.attributes.friendly_name||row.entity_id;}
    _format(state){return this._hass.formatEntityState?.(state)||state.state;}
    _disabled(row){return offline(this._hass.states[row.entity_id])||this._busy.has(row.entity_id);}
    _patchDOM(html){
      const template=document.createElement('template');template.innerHTML=html;
      const patch=(current,next)=>{
        if(current.nodeType!==next.nodeType||current.nodeName!==next.nodeName){
          const replacement=next.cloneNode(true);current.replaceWith(replacement);return;
        }
        if(current.nodeType===Node.TEXT_NODE||current.nodeType===Node.COMMENT_NODE){
          if(current.nodeValue!==next.nodeValue)current.nodeValue=next.nodeValue;
          return;
        }
        if(current.nodeType===Node.ELEMENT_NODE){
          for(const attribute of [...current.attributes])if(!next.hasAttribute(attribute.name))current.removeAttribute(attribute.name);
          for(const attribute of next.attributes)if(current.getAttribute(attribute.name)!==attribute.value)current.setAttribute(attribute.name,attribute.value);
        }
        for(let i=0;i<next.childNodes.length;i++){
          if(current.childNodes[i])patch(current.childNodes[i],next.childNodes[i]);
          else current.append(next.childNodes[i].cloneNode(true));
        }
        while(current.childNodes.length>next.childNodes.length)current.lastChild.remove();
        if(current.nodeType===Node.ELEMENT_NODE&&['INPUT','TEXTAREA','SELECT'].includes(current.tagName)&&this.shadowRoot.activeElement!==current){
          if(current.value!==next.value)current.value=next.value;
          if(current.tagName==='INPUT'&&current.type==='checkbox')current.checked=next.checked;
        }
      };
      // Keep ha-card/main alive: replacing the entire shadow tree briefly drops
      // its height and interrupts native scrolling/HA dashboard scroll anchoring.
      patch(this.shadowRoot,template.content);
    }
    _render(){
      if(!this._config||!this._hass)return;
      const visibleMain=this.shadowRoot.querySelector('main');
      const switchingView=this._renderedDevice!==this._selected||visibleMain?.dataset.tabContent!==this._tab;
      if(performance.now()<this._scrollUntil&&!switchingView){this._renderPending=true;return;}
      if(switchingView){this._scrollUntil=0;clearTimeout(this._scrollTimer);this._scrollTimer=null;}
      this._renderPending=false;
      // HA changes frequently. Keep the focused slider/text input intact.
      if(this.shadowRoot.activeElement?.matches('input,textarea,select'))return;
      const devices=this._registry?discover(this._registry.entities,this._registry.devices,this._hass.states):[];
      if(!this._selected&&devices.length)this._selected=devices[0].id;
      this._device=devices.find(d=>d.id===this._selected);
      const rows=this._rows();
      const signature=JSON.stringify([this._selected,this._tab,this._error,this._registryError,[...this._busy],[...this._composing],this._foldOpen,this._playlistDrafts.get(this._selected),this._ttsDrafts.get(this._selected),
        this._catalog,this._roomDrafts.get(this._selected),this._btOperations.get(this._selected),devices.map(d=>d.entities.filter(e=>domain(e.entity_id)==='media_player'||e.unique_id?.endsWith('_number_volume_state_number')).map(e=>this._hass.states[e.entity_id])),
        devices.map(d=>[d.id,d.name]),rows.map(e=>[e.entity_id,e.unique_id,this._hass.states[e.entity_id]])]);
      if(signature===this._signature)return;this._signature=signature;
      const oldMain=this.shadowRoot.querySelector('main');
      const sameView=this._renderedDevice===this._selected&&oldMain?.dataset.tabContent===this._tab;
      if(oldMain?.classList.contains('entity-scroll'))this._scrollPositions.set(this._renderedDevice+':'+oldMain.dataset.tabContent,oldMain.scrollTop);
      const tabs=[['media','mdi:music','Media'],['eq','mdi:equalizer','Equalizer'],['multiroom','mdi:speaker-multiple','Multiroom'],['bluetooth','mdi:bluetooth','Bluetooth'],['control','mdi:tune','Điều Khiển'],['status','mdi:information-outline','Trạng Thái']];
      this._patchDOM(`<style>${STYLE}</style><ha-card>
        <header><div class="brand"><ha-icon icon="mdi:speaker-wireless"></ha-icon><div><h2>${esc(this._config.title)}</h2><small>${esc(this._device?.name||'Chọn loa VBot')}</small></div></div>
        <button data-action="refresh" class="icon" title="Khám phá lại thiết bị" aria-label="Khám phá lại thiết bị"><ha-icon icon="mdi:refresh"></ha-icon></button></header>
        <div class="device"><label>Loa đang điều khiển<select data-device aria-label="Loa đang điều khiển"><option value="">Chọn loa</option>${devices.map(d=>`<option value="${esc(d.id)}" ${d.id===this._selected?'selected':''}>${esc(d.name)}</option>`).join('')}</select></label></div>
        <nav role="tablist">${tabs.map(([id,icon,name])=>`<button role="tab" aria-selected="${id===this._tab}" data-tab="${id}"><ha-icon icon="${icon}"></ha-icon>${name}</button>`).join('')}</nav>
        <main role="tabpanel" data-tab-content="${this._tab}" ${['multiroom','bluetooth','control','status'].includes(this._tab)?'class="entity-scroll" tabindex="0" aria-label="Danh sách thực thể có thể cuộn"':''}>${this._error?`<div class="error" role="alert">${esc(this._error)}</div>`:''}
        ${this._registryError?`<p class="error">${esc(this._registryError)}</p>`:''}
        ${!this._device?`<p class="empty">${this._loading?'Đang khám phá loa…':'Chưa tìm thấy loa. Kiểm tra tích hợp VBot Assistant, quyền truy cập hoặc nhấn khám phá lại.'}</p>`:this._content(rows)}</main>
        <footer>${rows.length} entity · Đồng bộ qua Home Assistant</footer></ha-card>`);
      this._renderedDevice=this._selected;
      this._measureMedia();
      const height=this._mediaHeights.get(this._selected);
      if(height){if(this.style.getPropertyValue('--vbot-tab-height')!==height+'px')this.style.setProperty('--vbot-tab-height',height+'px');}
      else if(this.style.getPropertyValue('--vbot-tab-height'))this.style.removeProperty('--vbot-tab-height');
      const main=this.shadowRoot.querySelector('main');
      if(!sameView&&main.classList.contains('entity-scroll')){
        const position=this._scrollPositions.get(this._selected+':'+this._tab)||0;
        if(main.scrollTop!==position)main.scrollTop=position;
      }
      this._updateProgress();this._scheduleClock();
      if(this._tab==='media'){
        const player=rows.find(e=>domain(e.entity_id)==='media_player');
        if(player&&(Number(this._hass.states[player.entity_id].attributes.supported_features||0)&131072)&&this._catalog?.entity!==player.entity_id)this._browse(player);
      }
    }
    _measureMedia(){
      if(performance.now()<this._scrollUntil){this._renderPending=true;return;}
      if(this._tab!=='media'||!this._device)return;
      const main=this.shadowRoot.querySelector('main[data-tab-content="media"]');if(!main)return;
      let height=main.getBoundingClientRect().height;
      // Match compact Media, even when the user has expanded a library/TTS panel.
      for(const details of main.querySelectorAll('details[open]')){
        for(const child of details.children){
          if(child.tagName==='SUMMARY')continue;
          const css=getComputedStyle(child);
          height-=child.getBoundingClientRect().height+(parseFloat(css.marginTop)||0)+(parseFloat(css.marginBottom)||0);
        }
      }
      if(height>0){height=Math.ceil(height);this._mediaHeights.set(this._selected,height);if(this.style.getPropertyValue('--vbot-tab-height')!==height+'px')this.style.setProperty('--vbot-tab-height',height+'px');}
    }
    _content(rows){
      if(this._tab==='multiroom')return this._multiroom();
      if(this._tab==='bluetooth')return this._bluetooth();
      if(this._tab==='eq')return this._equalizer();
      if(this._tab==='media'){
        const media=rows.filter(e=>domain(e.entity_id)==='media_player');
        return media.map(e=>this._media(e)).join('')+this._quickControls()+(!media.length?this._mediaSettings():'')+this._playlistPanel()+this._ttsPanel()+this._mediaLibrary(media[0])+this._mediaExtras(rows);
      }
      if(this._tab==='status')return this._status(rows);
      return this._group('Điều khiển và tác vụ',rows.filter(e=>!['sensor','binary_sensor','event','update','media_player'].includes(domain(e.entity_id))&&!this._eqField(e)&&!e.unique_id?.includes('_multiroom_')));
    }
    _status(rows){
      const groups={network:[],audio:[],system:[]},alerts=[];
      for(const row of rows.filter(e=>['sensor','binary_sensor','event','update'].includes(domain(e.entity_id)))){
        const key=(row.unique_id||row.entity_id).toLowerCase(),state=this._hass.states[row.entity_id];
        const group=/bluetooth|airplay|playback|audio|tts|wakeword|microphone|multiroom|volume/.test(key)?'audio':/wifi|wi_fi|ip_address|mqtt|mdns|server_|network|connectivity/.test(key)?'network':'system';
        groups[group].push(row);
        if(!state||offline(state))continue;
        const value=String(state.state).toLowerCase(),kind=domain(row.entity_id);
        if((kind==='binary_sensor'&&['problem','safety'].includes(state.attributes.device_class)&&value==='on')||/^(error|failed|lỗi)(\b|[:\s])/.test(value))alerts.push({row,text:this._format(state),error:true});
        else if(kind==='update'&&value==='on')alerts.push({row,text:'Có bản cập nhật',error:false});
        else if(/mqtt_connection/.test(key)&&['offline','disconnected','off','false','mất kết nối','không kết nối'].includes(value))alerts.push({row,text:'Mất kết nối MQTT',error:true});
        else if(/airplay_reconnecting/.test(key)&&['on','true','1'].includes(value))alerts.push({row,text:'Đang kết nối lại AirPlay',error:false});
      }
      const headings=[['network','Mạng và kết nối','mdi:lan'],['audio','Âm thanh và nguồn phát','mdi:speaker'],['system','Hệ thống và phiên bản','mdi:information-outline']];
      const noData=Object.values(groups).flat().every(row=>offline(this._hass.states[row.entity_id]));
      const notice=alerts.length?alerts.map(({row,text,error})=>`<div class="status-notice ${error?'is-error':''}" role="status"><ha-icon icon="${error?'mdi:alert-circle':'mdi:information'}"></ha-icon><span><strong>${esc(this._name(row))}</strong><br>${esc(text)}</span><button class="icon" data-more="${esc(row.entity_id)}" aria-label="Xem chi tiết"><ha-icon icon="mdi:chevron-right"></ha-icon></button></div>`).join(''):noData?'<p class="status-notice">Chưa nhận được trạng thái mới từ loa. Kiểm tra kết nối VBot/MQTT.</p>':'<p class="hint">Chưa có cảnh báo từ các thực thể.</p>';
      return notice+headings.filter(([key])=>groups[key].length).map(([key,title,icon])=>this._panelStart('status-'+key,`${title} · ${groups[key].length}`,icon)+`<div class="controls">${groups[key].map(row=>this._control(row)).join('')}</div></div></details>`).join('');
    }
    _bluetooth(){
      const entity=this._findEntity('select','_bluetooth_output_select');
      if(!entity)return '<p class="empty">Loa này chưa hỗ trợ quản lý Bluetooth. Cập nhật VBot và custom component.</p>';
      const state=this._hass.states[entity.entity_id],attrs=state?.attributes||{};
      if(offline(state))return '<p class="empty">VBot đang ngoại tuyến. Chạy VBot để quản lý kết nối Bluetooth.</p>';
      const devices=Array.isArray(attrs.devices)?attrs.devices:[];
      const connected=devices.filter(d=>d&&d.connected);
      const busy=this._busy.has(entity.entity_id),disabled=this._disabled(entity);
      const operation=this._btOperations.get(this._selected);
      const labels={scan:'Quét thiết bị',pair:'Ghép đôi',connect:'Kết nối loa/tai nghe',sink_connect:'Kết nối điện thoại',device_disconnect:'Ngắt kết nối'};
      const row=(device,active)=>{
        const current=devices.find(d=>d.mac===device.mac)||device;
        const action=active?'device_disconnect':!current.paired?'pair':current.audio_sink?'connect':current.audio_source?'sink_connect':null;
        const blocked=!active&&current.paired&&((current.audio_sink&&attrs.roles?.source===false)||(!current.audio_sink&&current.audio_source&&attrs.roles?.sink===false));
        const label=active?'Ngắt kết nối':!current.paired?'Ghép đôi':'Kết nối';
        const type=current.audio_sink&&current.audio_source?'Thiết bị âm thanh hai chiều':current.audio_sink?'Loa / tai nghe':current.audio_source?'Điện thoại / nguồn nhạc':'Thiết bị Bluetooth';
        const selected=Boolean(attrs.output_mac&&attrs.output_mac===current.mac);
        const audio=current.output_running||current.input_running?'Đang truyền âm thanh':current.output_connected||current.input_connected?'Đã kết nối âm thanh':active?'Đã kết nối Bluetooth':'Chưa kết nối';
        return `<div class="bt-device ${selected?'bt-output':''}"><ha-icon icon="${current.audio_sink?'mdi:speaker-bluetooth':current.audio_source?'mdi:cellphone-sound':'mdi:bluetooth'}"></ha-icon><div class="bt-name"><strong>${esc(current.name||current.mac)}</strong><small>${esc(current.mac)}</small><small>${type} · ${audio}</small>${selected?'<span class="badge">Đang làm đầu ra</span>':''}${blocked?'<small>A2DP tương ứng đang tắt trong cấu hình</small>':''}</div>${action?`<button data-bt-action="${action}" data-bt-mac="${esc(current.mac)}" ${disabled||blocked?'disabled':''}>${operation?.pending&&operation.mac===current.mac?'Đang xử lý…':esc(label)}</button>`:'<small>Chưa rõ chức năng âm thanh</small>'}</div>`;
      };
      const scanned=Array.isArray(attrs.scan_devices)?attrs.scan_devices.filter(d=>d&&d.mac&&!devices.some(current=>current.mac===d.mac&&current.connected)):[];
      const progress=operation?`<div class="status-notice ${operation.error?'is-error':''}" role="status"><ha-icon icon="${operation.pending?'mdi:loading':operation.error?'mdi:alert-circle':'mdi:check-circle'}"></ha-icon><span>${esc(labels[operation.action]||operation.action)}${operation.name?' · '+esc(operation.name):''}<br>${esc(operation.pending?'Đang chờ loa xác nhận…':operation.error||'Đã được loa xác nhận.')}</span></div>`:'';
      return `<p class="hint">Đầu ra hiện tại: <strong>${esc(attrs.output_mac?(attrs.output_name||connected.find(d=>d.mac===attrs.output_mac)?.name||attrs.output_mac):'Loa VBot')}</strong></p>${progress}<section class="media-panel"><h3>Thiết bị đang kết nối · ${connected.length}</h3>${connected.length?connected.map(d=>row(d,true)).join(''):'<p class="empty">Chưa có thiết bị Bluetooth đang kết nối.</p>'}</section>
        <section class="media-panel"><div class="section-title"><h3>Tìm thiết bị Bluetooth</h3><button data-bt-action="scan" ${disabled?'disabled':''}><ha-icon icon="${busy?'mdi:loading':'mdi:magnify'}"></ha-icon> ${busy?'Đang xử lý…':'Quét thiết bị'}</button></div>${scanned.map(d=>row(d,false)).join('')}${!scanned.length?`<p class="empty">${attrs.scan_id?'Không có thiết bị chưa kết nối trong kết quả quét.':'Bật chế độ ghép đôi trên thiết bị rồi nhấn quét.'}</p>`:''}</section>`;
    }
    async _bluetoothAction(action,mac=''){
      const entity=this._findEntity('select','_bluetooth_output_select');
      if(!entity||this._disabled(entity))return;
      const id=entity.entity_id;
      const selected=this._selected;
      const device=this._hass.states[id]?.attributes.devices?.find(d=>d.mac===mac);
      const operation={action,mac,name:device?.name||mac,pending:true,error:''};
      this._btOperations.set(selected,operation);
      this._busy.add(id);this._error='';this._signature='';this._queue();
      try{
        await this._hass.callService(DOMAIN,'bluetooth_command',{entity_id:id,action,...(mac?{mac}:{})});
      }catch(error){operation.error=error.message||'Không thực hiện được thao tác Bluetooth';}
      finally{operation.pending=false;this._busy.delete(id);this._signature='';this._queue();}
    }
    _roomPlayers(){
      return discover(this._registry?.entities||[],this._registry?.devices||[],this._hass.states).map(device=>{
        const player=device.entities.find(e=>domain(e.entity_id)==='media_player'&&(!this._config.entities||this._config.entities.includes(e.entity_id)));
        return player?{...device,player,state:this._hass.states[player.entity_id]}:null;
      }).filter(p=>p&&(Number(p.state.attributes.supported_features||0)&524288));
    }
    _multiroom(){
      const players=this._roomPlayers(),host=players.find(p=>p.id===this._selected);
      if(!host)return '<p class="empty">Chưa có Media Player để điều khiển Multiroom.</p>';
      const a=host.state.attributes,members=Array.isArray(a.group_members)?a.group_members:[];
      const selected=this._roomDrafts.get(this._selected)||members;
      const canJoin=Boolean(Number(a.supported_features||0)&524288),busy=this._busy.has(host.player.entity_id);
      const linked=a.multiroom_connected===true;
      const group=this._findEntity('select','_multiroom_group_selected');
      return `<section><div class="section-title"><h3>Multiroom · ${esc(host.name)}</h3><span class="badge">${offline(host.state)?'Mất kết nối':linked?'Đang kết nối':'Phát tại loa'}</span></div>
        <p class="hint">Loa đang điều khiển làm loa chủ khi ghép nhóm mới. Chọn các loa muốn phát cùng rồi nhấn áp dụng.</p>
        ${a.multiroom_coordinator?`<p class="hint">Loa chủ hiện tại: ${esc(a.multiroom_coordinator)}</p>`:''}
        <div class="room-list">${players.map(p=>{
          const own=p.id===host.id,disabled=offline(p.state)||busy||!canJoin;
          const rawVolume=p.state.attributes.volume_level,volume=Number(rawVolume),valid=rawVolume!==null&&rawVolume!==undefined&&Number.isFinite(volume)&&volume>=0&&volume<=1;
          return `<div class="room-speaker"><label class="room-choice"><input type="checkbox" data-room-member="${esc(p.player.entity_id)}" ${own||selected.includes(p.player.entity_id)?'checked':''} ${own||disabled?'disabled':''}><ha-icon icon="mdi:speaker"></ha-icon><span><strong>${esc(p.name)}</strong><small>${own?'Loa đang điều khiển':members.includes(p.player.entity_id)?'Trong nhóm hiện tại':'Chưa thuộc nhóm'} · ${offline(p.state)?'Mất kết nối':'Sẵn sàng'}</small></span></label><div class="range"><input aria-label="Âm lượng ${esc(p.name)}" type="range" min="0" max="100" step="1" data-room-volume="${esc(p.player.entity_id)}" value="${valid?Math.round(volume*100):0}" ${offline(p.state)||!valid||!(Number(p.state.attributes.supported_features||0)&4)||this._busy.has(p.player.entity_id)?'disabled':''}><output>${valid?Math.round(volume*100)+'%':'Chưa có âm lượng'}</output></div></div>`;
        }).join('')}</div>
        <div class="room-actions"><button class="action-primary" data-room-action="join" ${!canJoin||offline(host.state)||busy?'disabled':''}>Áp dụng nhóm loa</button><button data-room-action="leave" ${!linked||offline(host.state)||busy?'disabled':''}>Rời nhóm / Phát về loa</button></div>
        ${!canJoin?'<p class="hint">Media Player chưa hỗ trợ ghép nhóm. Cập nhật tích hợp VBot.</p>':''}
        ${group?`<section class="media-panel"><h3>Nhóm đã lưu trên loa</h3>${this._control(group)}</section>`:''}
        ${this._group('Điều khiển nhóm',this._rows().filter(e=>domain(e.entity_id)==='button'&&e.unique_id?.includes('_multiroom_')))}</section>`;
    }
    async _roomAction(action){
      const host=this._roomPlayers().find(p=>p.id===this._selected);if(!host||offline(host.state))return;
      const id=host.player.entity_id;
      if(action==='leave'){
        if(window.confirm('Rời nhóm Multiroom? Nếu đây là loa chủ, cả nhóm sẽ ngừng phát chung.'))await this._service(id,'unjoin');
      }else{
        const members=[...this.shadowRoot.querySelectorAll('[data-room-member]:checked')].map(e=>e.dataset.roomMember).filter(e=>e!==id);
        const valid=new Set(this._roomPlayers().filter(p=>!offline(p.state)).map(p=>p.player.entity_id));
        if(members.some(e=>!valid.has(e)))return;
        if(!members.length){this._error='Chọn ít nhất một loa khác để ghép nhóm.';this._signature='';this._queue();return;}
        if(await this._service(id,'join',{group_members:members})){
          this._roomDrafts.delete(host.id);this._signature='';this._queue();
        }
      }
    }
    async _roomVolume(id,value){
      const p=this._roomPlayers().find(p=>p.player.entity_id===id),volume=Number(value);
      if(!p||offline(p.state)||!(Number(p.state.attributes.supported_features||0)&4)||!Number.isFinite(volume)||this._busy.has(id))return;
      const generation=this._generation;
      this._busy.add(id);this._error='';this._queue();
      try{await this._hass.callService('media_player','volume_set',{entity_id:id,volume_level:Math.max(0,Math.min(100,volume))/100});}
      catch(error){if(generation===this._generation)this._error=error.message||'Không đổi được âm lượng';}
      finally{this._busy.delete(id);this._signature='';this._queue();}
    }
    _eqField(e){return /_equalizer_(preset|bass_db|low_mid_db|mid_db|high_mid_db|treble_db|air_db|preamp_db|wet_percent)$/.test(e.unique_id||'');}
    _group(title,rows){return `<section><h3>${esc(title)}</h3><div class="controls">${rows.length?rows.map(e=>this._control(e)).join(''):'<p class="empty">Loa này chưa cung cấp entity cho mục này.</p>'}</div></section>`;}
    _equalizer(){
      const preset=this._eq('preset');const active=preset?this._hass.states[preset.entity_id]?.attributes.eq_active:null;
      const bandRows=EQ.map(([key])=>this._eq(key));
      return `<section><div class="section-title"><h3>Chế độ âm thanh - EQ</h3><span class="badge">${active===true?'EQ đang bật':active===false?'EQ đang tắt':'Chưa có trạng thái EQ'}</span></div>
        ${preset?this._control(preset):'<p class="empty">Chưa có preset EQ. Cập nhật VBot và tích hợp Home Assistant.</p>'}
        <div class="eq">${EQ.map(([key,freq,label],i)=>{
          const row=bandRows[i];if(!row)return `<div class="band"><strong>${freq}</strong><small>${label}</small><span class="muted">Chưa hỗ trợ</span></div>`;
          const s=this._hass.states[row.entity_id];return `<div class="band"><strong>${freq}</strong><small>${label}</small>${this._range(row,true)}<button class="value" data-more="${esc(row.entity_id)}" data-value="${esc(row.entity_id)}">${esc(s.state)} dB</button></div>`;
        }).join('')}</div>
        ${['preamp_db','wet_percent'].map(key=>this._eq(key)).filter(Boolean).map(e=>this._control(e)).join('')}
        </section>`;
    }
    _range(row,vertical=false){
      const s=this._hass.states[row.entity_id],a=s.attributes;
      return `<input type="range" ${vertical?'class="vertical"':''} data-entity="${esc(row.entity_id)}" data-kind="number" data-unit="${esc(a.unit_of_measurement||'')}" min="${Number(a.min??0)}" max="${Number(a.max??100)}" step="${Number(a.step??1)}" value="${Number(s.state)||0}" aria-label="${esc(this._name(row))}" ${this._disabled(row)?'disabled':''}>`;
    }
    _control(row,label=null){
      const s=this._hass.states[row.entity_id],a=s.attributes,d=domain(row.entity_id),disabled=this._disabled(row)?'disabled':'';
      const id=esc(row.entity_id),name=esc(label||this._name(row));let control;
      if(d==='number')control=`<div class="range">${this._range(row)}<output data-value="${id}">${esc(s.state)} ${esc(a.unit_of_measurement||'')}</output></div>`;
      else if(d==='select'){
        const options=Array.isArray(a.options)?a.options:[];
        control=`<div><select aria-label="${name}" data-entity="${id}" data-kind="select" ${disabled}>${!options.includes(s.state)?'<option value="" selected disabled>Chưa xác định</option>':''}${options.map(o=>`<option value="${esc(o)}" ${o===s.state?'selected':''}>${esc(o)}</option>`).join('')}</select>${a.last_source_error?`<p class="search-error" role="alert">${esc(a.last_source_error)}</p>`:''}</div>`;
      }
      else if(['switch','input_boolean'].includes(d))control=`<button role="switch" aria-checked="${s.state==='on'}" class="toggle ${s.state==='on'?'on':''}" data-toggle="${id}" ${disabled}>${s.state==='on'?'Đang bật':'Đang tắt'}</button>`;
      else if(['text','input_text'].includes(d))control=`<div class="text"><input type="${a.mode==='password'?'password':'text'}" data-entity="${id}" data-kind="text" aria-label="${name}" value="${esc(s.state)}" maxlength="${Number(a.max??255)}" ${disabled}><button data-save="${id}" ${disabled}>Lưu</button></div>`;
      else if(['button','script','scene','input_button'].includes(d))control=`<button data-execute="${id}" ${disabled}>Thực hiện</button>`;
      else control=`<button class="value" data-more="${id}">${esc(this._format(s))}</button>`;
      return `<div class="row"><button class="label" data-more="${id}" title="${id}">${name}</button>${control}</div>`;
    }
    _media(row){
      const s=this._hass.states[row.entity_id],a=s.attributes,id=esc(row.entity_id),disabled=this._disabled(row)?'disabled':'';
      const features=Number(a.supported_features||0);
      const image=this._image(a.entity_picture_local||a.entity_picture);
      const duration=Number(a.media_duration),finiteDuration=Number.isFinite(duration)&&duration>0;
      const position=this._position(s),seek=finiteDuration&&(features&2)!==0;
      const actions=[['media_previous_track','mdi:skip-previous','Bài trước',16],
        [s.state==='playing'?'media_pause':'media_play',s.state==='playing'?'mdi:pause':'mdi:play',s.state==='playing'?'Tạm dừng':'Phát',s.state==='playing'?1:16384],
        ['media_stop','mdi:stop','Dừng',4096],['media_next_track','mdi:skip-next','Bài tiếp',32]];
      return `<section class="player ${image?'has-art':''}">${image?`<img class="art-background" src="${esc(image)}" alt="" referrerpolicy="no-referrer">`:''}<div class="player-content">
        ${this._connectionStatus(s)}
        <div class="player-top"><span class="playing-state"><span class="state-dot ${s.state==='playing'?'live':''}"></span>${esc(this._format(s))}</span><span class="source-chip">${esc(a.source||a.source_kind||'VBot')}</span></div>
        <div class="track"><div class="cover"><ha-icon icon="mdi:music-note"></ha-icon>${image?`<img src="${esc(image)}" alt="Ảnh bìa bài hát" referrerpolicy="no-referrer">`:''}</div>
        <div class="track-text"><small>ĐANG PHÁT</small><h3>${esc(a.media_title||'Sẵn sàng phát nhạc')}</h3><p>${esc(a.media_artist||this._name(row))}</p>${a.media_album_name?`<small>${esc(a.media_album_name)}</small>`:''}</div></div>
        <div class="timeline"><input type="range" data-kind="seek" data-progress="${id}" data-entity="${id}" min="0" max="${finiteDuration?duration:1}" step="1" value="${position}" aria-label="Tua bài hát" ${!seek||disabled?'disabled':''}>
          <div class="times"><span data-elapsed="${id}">${this._time(position)}</span><span>${finiteDuration?this._time(duration):'Trực tiếp / Không có thời lượng'}</span></div></div>
        <div class="transport">${actions.filter(x=>(features&x[3])!==0).map(([action,icon,label])=>`<button class="icon ${action==='media_play'||action==='media_pause'?'primary-play':''}" data-media="${action}" data-entity="${id}" title="${label}" aria-label="${label}" ${disabled}><ha-icon icon="${icon}"></ha-icon></button>`).join('')}
          ${(features&8)!==0?`<button class="icon ${a.is_volume_muted?'muted-volume':''}" data-volume-mute="${id}" title="${a.is_volume_muted?'Bật âm thanh':'Tắt âm thanh loa'}" aria-label="${a.is_volume_muted?'Bật âm thanh':'Tắt âm thanh loa'}" aria-pressed="${!!a.is_volume_muted}" ${disabled}><ha-icon icon="${a.is_volume_muted?'mdi:volume-off':'mdi:volume-high'}"></ha-icon></button>`:''}</div>
        ${this._mediaSettings(true)}
        ${a.playlist_name?`<div class="playlist-caption"><ha-icon icon="mdi:playlist-music"></ha-icon>${esc(a.playlist_name)}${a.playlist_total?' · '+esc(Number(a.playlist_index??0)+1)+' / '+esc(a.playlist_total):''}</div>`:''}</div></section>`;
    }
    _image(value){
      if(typeof value!=='string'||!value||value.length>8192)return '';
      try{
        const url=new URL(value,location.href);
        if(!['http:','https:'].includes(url.protocol)||url.username||url.password)return '';
        return value.startsWith('/')&&!value.startsWith('//')?(this._hass.hassUrl?.(value)||value):url.href;
      }catch(_){return '';}
    }
    _connectionStatus(player){
      const sensor=this._findEntity('sensor','_sensor_bluetooth_connection_state_sensor');
      const binary=this._findEntity('binary_sensor','_bluetooth_connected_binary_sensor');
      const device=this._findEntity('sensor','_sensor_bluetooth_device_name_state_sensor');
      const normalize=value=>{
        const text=String(value??'').trim().toLocaleLowerCase();
        if(['on','true','1','connected','online','đã kết nối'].includes(text))return true;
        if(['off','false','0','disconnected','not connected','chưa kết nối','không kết nối','mất kết nối'].includes(text))return false;
        return null;
      };
      const state=row=>row&&!offline(this._hass.states[row.entity_id])?this._hass.states[row.entity_id].state:null;
      // The host publishes Vietnamese text; prefer it over legacy binary mappings.
      let bluetooth=normalize(state(sensor))??normalize(state(binary));
      let name=state(device);
      if(!name||['không kết nối','chưa kết nối','không có dữ liệu','n/a','none'].includes(String(name).trim().toLocaleLowerCase()))name='';
      const output=this._findEntity('select','_bluetooth_output_select');
      const outputState=output&&this._hass.states[output.entity_id];
      const snapshot=outputState?.attributes;
      let count=0;
      if(outputState&&!offline(outputState)&&outputState.state!=='unknown'&&Array.isArray(snapshot?.devices)){
        const connected=[...new Map(snapshot.devices.filter(d=>d?.connected&&d.mac).map(d=>[d.mac,d])).values()];
        count=connected.length;bluetooth=count>0;
        name=connected.map(d=>d.name||d.mac).join(', ');
      }
      const a=player.attributes;
      const multiroom=offline(player)?null:typeof a.multiroom_connected==='boolean'?a.multiroom_connected:Array.isArray(a.group_members)?a.group_members.length>1:null;
      const chip=(kind,connected,text,icon,tab='')=>`<${tab?'button type="button"':'div'} class="connection ${connected===true?'connected':connected===false?'disconnected':'unknown'}" data-connection="${kind}" ${tab?`data-tab="${tab}" aria-label="Xem các thiết bị Bluetooth đang kết nối"`:'role="status"'}><ha-icon icon="${icon}"></ha-icon><div><strong>${kind==='bluetooth'?'Bluetooth':'Multiroom'}</strong><span>${esc(text)}</span></div></${tab?'button':'div'}>`;
      const bluetoothText=count>2?`${count} thiết bị đang kết nối`:bluetooth===true?(name?'Đã kết nối · '+name:'Đã kết nối · Chưa có tên thiết bị'):bluetooth===false?'Chưa kết nối':'Chưa có trạng thái';
      return `<div class="connection-status">${chip('bluetooth',bluetooth,bluetoothText,'mdi:bluetooth',count>0?'bluetooth':'')}${chip('multiroom',multiroom,multiroom===true?'Đã kết nối':multiroom===false?'Chưa kết nối':'Chưa có trạng thái','mdi:speaker-multiple')}</div>`;
    }
    _time(value){
      if(!Number.isFinite(value)||value<0)return '0:00';
      const seconds=Math.floor(value),h=Math.floor(seconds/3600),m=Math.floor(seconds%3600/60),s=String(seconds%60).padStart(2,'0');
      return h?`${h}:${String(m).padStart(2,'0')}:${s}`:`${m}:${s}`;
    }
    _position(state){
      const a=state.attributes,raw=Number(a.media_position),start=Date.parse(a.media_position_updated_at);
      let position=Number.isFinite(raw)?Math.max(0,raw):0;
      if(state.state==='playing'&&Number.isFinite(start))position+=Math.max(0,(Date.now()-start)/1000);
      const duration=Number(a.media_duration);
      return Number.isFinite(duration)&&duration>0?Math.min(duration,position):position;
    }
    _updateProgress(){
      if(performance.now()<this._scrollUntil)return;
      for(const range of this.shadowRoot.querySelectorAll('[data-progress]')){
        const state=this._hass?.states[range.dataset.entity];if(!state||this.shadowRoot.activeElement===range)continue;
        const position=this._position(state);range.value=position;
        const label=this.shadowRoot.querySelector(`[data-elapsed="${CSS.escape(range.dataset.entity)}"]`);
        if(label)label.textContent=this._time(position);
      }
    }
    _scheduleClock(){
      clearTimeout(this._clock);this._clock=null;
      if(!this.isConnected||this._tab!=='media'||document.visibilityState==='hidden'||!this._rows().some(e=>domain(e.entity_id)==='media_player'&&this._hass.states[e.entity_id]?.state==='playing'))return;
      this._clock=setTimeout(()=>{this._clock=null;this._updateProgress();this._scheduleClock();},1000);
    }
    _quickControls(){
      const rows=this._rows(),find=(d,suffix)=>rows.find(e=>domain(e.entity_id)===d&&e.unique_id?.endsWith(suffix));
      const mic=find('switch','_switch_mic_on_off_state_switch');
      const wake=find('button','_wakeup')||find('switch','_switch_conversation_mode_flag_state_switch');
      const loop=find('switch','_switch_playlist_loop_state_switch');
      const conversation=find('switch','_switch_conversation_mode_state_switch');
      const controls=[[mic,'Mic',this._hass.states[mic?.entity_id]?.state==='on'?'mdi:microphone':'mdi:microphone-off','toggle'],
        [wake,'Wakeup','mdi:microphone-message',wake&&domain(wake.entity_id)==='button'?'press':'turn_on'],
        [loop,'Lặp nhạc','mdi:repeat','toggle'],[conversation,'Hội thoại','mdi:chat-processing-outline','toggle']].filter(x=>x[0]);
      return `<div class="quick-controls">${controls.map(([row,label,icon,service])=>{
        const on=this._hass.states[row.entity_id]?.state==='on';
        return `<button class="quick ${on?'enabled':''}" data-quick="${esc(row.entity_id)}" data-quick-service="${service}" title="${label}" aria-label="${label}" ${service==='toggle'?`aria-pressed="${on}"`:''} ${this._disabled(row)?'disabled':''}><ha-icon icon="${icon}"></ha-icon><span>${label}</span>${service==='toggle'?`<small>${on?'Bật':'Tắt'}</small>`:''}</button>`;
      }).join('')}<button class="quick" data-tab="control"><ha-icon icon="mdi:dots-horizontal"></ha-icon><span>Tác vụ khác</span></button></div>`;
    }
    _mediaExtras(rows){
      const suffixes=['_main_processing','_news_paper_player','_media_control_play','_bluetooth_disconnect','_bluetooth_pairing'];
      const selected=rows.filter(e=>(domain(e.entity_id)==='text'&&!e.unique_id?.endsWith('_vbot_tts'))||(domain(e.entity_id)==='button'&&suffixes.some(s=>e.unique_id?.endsWith(s))));
      return selected.length?`<details data-media-extras class="media-extras" ${this._extrasOpen?'open':''}><summary><ha-icon icon="mdi:message-text-outline"></ha-icon> Thông báo, URL nhạc và tác vụ mở rộng</summary>${this._group('Lưu nội dung rồi nhấn tác vụ tương ứng',selected)}</details>`:'';
    }
    _mediaSettings(inline=false){
      const volume=this._findEntity('number','_number_volume_state_number');
      const source=this._findEntity('select','_media_source_select');
      const output=this._findEntity('select','_bluetooth_output_select');
      if(!volume&&!source&&!output)return '';
      return `<section class="${inline?'player-settings':'media-panel'}">${inline?'':'<h3><ha-icon icon="mdi:speaker-wireless"></ha-icon> Âm lượng và nguồn phát</h3>'}${volume?this._control(volume,'Âm lượng loa'):''}${source?this._control(source,'Chuyển nguồn phát đầu vào'):''}${output?this._control(output,'Chuyển nguồn phát đầu ra:'):''}</section>`;
    }
    _panelStart(key,title,icon,className='media-panel'){
      return `<details class="${className} fold-panel" data-fold="${key}" ${this._foldOpen[key]?'open':''}><summary><ha-icon icon="${icon}"></ha-icon><span>${title}</span><ha-icon class="fold-chevron" icon="mdi:chevron-down"></ha-icon></summary><div class="fold-body">`;
    }
    _playlistPanel(){
      const select=this._findEntity('select','_playlist_selected'),play=this._findEntity('button','_playlist_play_selected');
      if(!select)return '';
      const state=this._hass.states[select.entity_id],options=Array.isArray(state.attributes.options)?state.attributes.options:[];
      const draft=this._playlistDrafts.get(this._selected),chosen=options.includes(draft)?draft:state.state;
      const busy=this._composing.has('playlist:'+this._selected);
      return this._panelStart('playlist','Playlist','mdi:playlist-play')+`<div class="playlist-picker"><select data-playlist-choice aria-label="Chọn playlist để phát" ${this._disabled(select)||busy?'disabled':''}>${options.map(option=>`<option value="${esc(option)}" ${option===chosen?'selected':''}>${esc(option)}</option>`).join('')}</select><button data-play-playlist class="action-primary" ${!play||this._disabled(play)||this._disabled(select)||busy||!options.includes(chosen)?'disabled':''}><ha-icon icon="mdi:play"></ha-icon> ${busy?'Đang mở…':'Phát playlist'}</button></div>${!options.length?'<p class="hint">Chưa có playlist. Tạo playlist trên WebUI của loa rồi đồng bộ trạng thái.</p>':''}</div></details>`;
    }
    _ttsPanel(){
      const text=this._findEntity('text','_vbot_tts'),play=this._findEntity('button','_vbot_tts');
      if(!text||!play)return '';
      const state=this._hass.states[text.entity_id],busy=this._composing.has('tts:'+this._selected);
      const draft=this._ttsDrafts.get(this._selected)??'';
      return this._panelStart('tts','Phát thông báo — TTS','mdi:bullhorn-outline')+`<textarea data-tts-draft aria-label="Nội dung thông báo TTS" rows="3" maxlength="${Number(state.attributes.max??255)}" placeholder="Nhập nội dung muốn loa đọc…" ${this._disabled(text)||this._disabled(play)||busy?'disabled':''}>${esc(draft)}</textarea><div class="tts-actions"><small class="hint">Phát trên ${esc(this._device.name)}</small><button data-send-tts class="action-primary" ${this._disabled(text)||this._disabled(play)||busy?'disabled':''}><ha-icon icon="mdi:send"></ha-icon> ${busy?'Đang gửi…':'Phát TTS'}</button></div></div></details>`;
    }
    async _compose(kind){
      const key=kind+':'+this._selected;if(this._composing.has(key))return;
      const generation=this._generation;
      const input=kind==='playlist'?this._findEntity('select','_playlist_selected'):this._findEntity('text','_vbot_tts');
      const play=this._findEntity('button',kind==='playlist'?'_playlist_play_selected':'_vbot_tts');
      if(!input||!play||this._disabled(input)||this._disabled(play))return;
      let value;
      if(kind==='playlist'){
        value=this.shadowRoot.querySelector('[data-playlist-choice]')?.value;
        if(!this._hass.states[input.entity_id].attributes.options?.includes(value))return;
      }else{
        value=this.shadowRoot.querySelector('[data-tts-draft]')?.value.trim();
        if(!value){this._error='Nhập nội dung TTS trước khi phát.';this._queue();return;}
        if(value.length>Number(this._hass.states[input.entity_id].attributes.max??255)){this._error='Nội dung TTS vượt giới hạn ký tự.';this._queue();return;}
        this._ttsDrafts.set(this._selected,value);
      }
      this._composing.add(key);this._queue();
      try{
        const saved=await this._service(input.entity_id,kind==='playlist'?'select_option':'set_value',kind==='playlist'?{option:value}:{value});
        if(saved&&generation===this._generation){
          const played=await this._service(play.entity_id,'press');
          if(played&&kind==='playlist'&&generation===this._generation)this._playlistDrafts.delete(this._selected);
        }
      }finally{this._composing.delete(key);this._signature='';this._queue();}
    }
    _mediaLibrary(player){
      if(!player||!(Number(this._hass.states[player.entity_id].attributes.supported_features||0)&131072))return '';
      const c=this._catalog?.entity===player.entity_id?this._catalog:null;
      return this._panelStart('library','Khám phá âm nhạc','mdi:music-box-multiple-outline','library')+`<div class="library-toolbar"><button class="icon" data-library="root" title="Mở thư viện nhạc" aria-label="Mở thư viện nhạc"><ha-icon icon="mdi:folder-music-outline"></ha-icon> Thư viện nhạc</button></div>
        <div class="search-bar"><select data-search-source aria-label="Nguồn tìm kiếm"><option value="">Tất cả nguồn</option>${(c?.sources||[]).filter(x=>x.can_search).map((x,i)=>`<option value="${esc(x.media_content_id)}" ${x.media_content_id===c?.sourceId?'selected':''}>${esc(x.title)}</option>`).join('')}</select>
        <div class="search-query"><input type="search" data-search-query aria-label="Tìm bài hát, ca sĩ hoặc podcast" maxlength="256" placeholder="Bài hát, ca sĩ, podcast…" value="${esc(c?.query||'')}"><button data-library="search" class="search-button" aria-label="Tìm kiếm nhạc" ${c?.busy||this._disabled(player)?'disabled':''}><ha-icon icon="mdi:magnify"></ha-icon></button></div></div>
        <div class="source-shortcuts">${(c?.sources||[]).map((x,i)=>`<button data-source="${i}" ${c?.busy?'disabled':''}>${esc(x.title)}</button>`).join('')}</div>
        ${c?.busy?'<p role="status" class="empty">Đang tải nhạc…</p>':''}${c?.error?`<p role="alert" class="search-error">${esc(c.error)}</p>`:''}
        ${c?.history?.length?'<button data-library="back" class="back"><ha-icon icon="mdi:chevron-left"></ha-icon> Quay lại</button>':''}
        ${c?.title?`<h4 class="result-title">${esc(c.title)}</h4>`:''}
        <div class="results">${(c?.items||[]).map((item,i)=>{
          const image=this._image(item.thumbnail);
          return `<div class="result"><div class="result-cover"><ha-icon icon="${item.can_expand?'mdi:folder-music':'mdi:music-note'}"></ha-icon>${image?`<img src="${esc(image)}" alt="" loading="lazy" referrerpolicy="no-referrer">`:''}</div><div class="result-name">${esc(item.title)}</div>${item.can_expand?`<button class="icon" data-browse="${i}" aria-label="Mở ${esc(item.title)}" ${c?.busy?'disabled':''}><ha-icon icon="mdi:chevron-right"></ha-icon></button>`:''}${item.can_play?`<button class="icon" data-play-result="${i}" aria-label="Phát ${esc(item.title)}" ${this._disabled(player)?'disabled':''}><ha-icon icon="mdi:play-circle"></ha-icon></button>`:''}</div>`;
        }).join('')}</div>${c&&!c.busy&&!c.items?.length&&!c.error?'<p class="empty">Chọn nguồn để duyệt nhạc hoặc nhập từ khóa và tìm kiếm.</p>':''}</div></details>`;
    }
    async _mediaRequest(request){
      let timeout;
      try{return await Promise.race([this._hass.callWS(request),new Promise((_,reject)=>{timeout=setTimeout(()=>reject(Error('Hết thời gian chờ. Hãy thử lại.')),45000);})]);}
      finally{clearTimeout(timeout);}
    }
    async _browse(player,item=null,back=false){
      if(this._catalog?.busy)return;
      if(!player||!this._rows().some(e=>e.entity_id===player.entity_id)||offline(this._hass.states[player.entity_id]))return;
      if(this._catalog?.entity!==player.entity_id)this._catalog={entity:player.entity_id,sources:[],items:[],history:[],query:'',sourceId:''};
      const c=this._catalog,generation=this._generation,seq=++this._requestSeq;
      c.busy=true;c.error='';this._queue();
      try{
        const result=await this._mediaRequest({type:'media_player/browse_media',entity_id:player.entity_id,...(item?{media_content_id:item.media_content_id,media_content_type:item.media_content_type}:{})});
        if(generation!==this._generation||seq!==this._requestSeq)return;
        const items=Array.isArray(result.children)?result.children.filter(x=>x&&typeof x.media_content_id==='string').slice(0,200):[];
        if(!item){c.sources=items;c.root=result;c.history=[];c.items=[];c.title='';}
        else{if(!back)c.history.push(c.current||null);c.items=items;c.title=result.title||item.title;}
        c.current=item;
      }catch(error){if(generation===this._generation)c.error=error.message||'Không tải được thư viện nhạc';}
      finally{if(generation===this._generation&&seq===this._requestSeq){c.busy=false;this._signature='';this._queue();}}
    }
    async _search(){
      const c=this._catalog;if(!c||c.busy)return;
      if(!this._rows().some(e=>e.entity_id===c.entity)||offline(this._hass.states[c.entity]))return;
      const query=this.shadowRoot.querySelector('[data-search-query]')?.value.trim().slice(0,256);
      if(!query)return;
      const sourceId=this.shadowRoot.querySelector('[data-search-source]')?.value||'';
      const source=c.sources.find(x=>x.can_search&&x.media_content_id===sourceId);
      c.query=query;c.sourceId=source?.media_content_id||'';c.busy=true;c.error='';
      const generation=this._generation,seq=++this._requestSeq;this._queue();
      try{
        const result=await this._mediaRequest({type:'media_player/search_media',entity_id:c.entity,search_query:query,
          ...(source?{media_content_id:source.media_content_id,media_content_type:source.media_content_type}:{} )});
        if(generation!==this._generation||seq!==this._requestSeq)return;
        c.items=Array.isArray(result.result)?result.result.filter(x=>x&&typeof x.media_content_id==='string').slice(0,200):[];
        c.history=[];c.current=null;c.title=`Kết quả: ${query}`;
        if(!c.items.length)c.error='Không tìm thấy kết quả phù hợp.';
      }catch(error){if(generation===this._generation)c.error=error.message||'Không tìm được nhạc';}
      finally{if(generation===this._generation&&seq===this._requestSeq){c.busy=false;this._signature='';this._queue();}}
    }
    async _service(id,service,data={}){
      if(this._busy.has(id)||!this._rows().some(e=>e.entity_id===id)||offline(this._hass.states[id]))return false;
      const generation=this._generation;
      this._busy.add(id);this._error='';this._queue();
      try{await this._hass.callService(domain(id),service,{entity_id:id,...data});return true;}
      catch(error){if(generation===this._generation)this._error=error.message||'Không thực hiện được lệnh';return false;}
      finally{this._busy.delete(id);this._signature='';this._queue();}
    }
    _click(event){
      const b=event.target.closest('button');if(!b||b.disabled)return;
      this._scrollUntil=0;clearTimeout(this._scrollTimer);this._scrollTimer=null;
      if(b.dataset.tab){this._tab=b.dataset.tab;this._signature='';this._queue();}
      if(b.dataset.btAction)this._bluetoothAction(b.dataset.btAction,b.dataset.btMac||'');
      if(b.dataset.roomAction)this._roomAction(b.dataset.roomAction);
      if(b.dataset.action==='refresh')this._loadRegistry();
      if(b.dataset.more)this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:b.dataset.more},bubbles:true,composed:true}));
      if(b.dataset.toggle)this._service(b.dataset.toggle,'toggle');
      if(b.dataset.quick)this._service(b.dataset.quick,b.dataset.quickService);
      if(b.dataset.media)this._service(b.dataset.entity,b.dataset.media);
      if(b.hasAttribute('data-play-playlist'))this._compose('playlist');
      if(b.hasAttribute('data-send-tts'))this._compose('tts');
      if(b.dataset.volumeMute){
        const id=b.dataset.volumeMute;
        this._service(id,'volume_mute',{is_volume_muted:!this._hass.states[id]?.attributes.is_volume_muted});
      }
      if(b.dataset.library==='search')this._search();
      if(b.dataset.library==='root'){
        const player=this._rows().find(e=>domain(e.entity_id)==='media_player');
        if(this._catalog&&!this._catalog.busy&&this._catalog.root){this._catalog.items=this._catalog.sources;this._catalog.history=[];this._catalog.current=null;this._catalog.title='Thư viện nhạc';this._catalog.error='';this._signature='';this._queue();}
        else if(this._catalog&&!this._catalog.busy)this._browse(player);
        else if(!this._catalog)this._browse(player);
      }
      if(b.dataset.library==='back'&&this._catalog&&!this._catalog.busy){
        const item=this._catalog.history.pop();
        this._browse(this._rows().find(e=>e.entity_id===this._catalog.entity),item,true);
      }
      if(b.hasAttribute('data-source')||b.hasAttribute('data-browse')){
        const c=this._catalog;
        const item=b.hasAttribute('data-source')?c?.sources[Number(b.dataset.source)]:c?.items[Number(b.dataset.browse)];
        if(item?.can_expand&&!c.busy)this._browse(this._rows().find(e=>e.entity_id===c.entity),item);
      }
      if(b.hasAttribute('data-play-result')){
        const c=this._catalog,item=c?.items[Number(b.dataset.playResult)];
        if(item?.can_play)this._service(c.entity,'play_media',{media_content_id:item.media_content_id,media_content_type:item.media_content_type||'music'});
      }
      if(b.dataset.save){
        const input=this.shadowRoot.querySelector(`input[data-entity="${CSS.escape(b.dataset.save)}"]`);
        if(input)this._service(b.dataset.save,'set_value',{value:input.value});
      }
      if(b.dataset.execute){
        const id=b.dataset.execute;
        // Buttons can reboot or delete data. Never execute merely by rendering.
        if(window.confirm(`Thực hiện: ${this._hass.states[id]?.attributes.friendly_name||id}?`))
          this._service(id,['script','scene'].includes(domain(id))?'turn_on':'press');
      }
    }
    _change(event){
      const t=event.target;
      this._scrollUntil=0;clearTimeout(this._scrollTimer);this._scrollTimer=null;
      if(t.hasAttribute('data-device')){this._selectDevice(t.value);t.blur();this._queue();return;}
      if(t.hasAttribute('data-room-member')){this._roomDrafts.set(this._selected,[...this.shadowRoot.querySelectorAll('[data-room-member]:checked')].map(e=>e.dataset.roomMember));t.blur();this._signature='';this._queue();return;}
      if(t.hasAttribute('data-room-volume')){
        this._roomVolume(t.dataset.roomVolume,t.value);t.blur();return;
      }
      if(t.hasAttribute('data-playlist-choice')){this._playlistDrafts.set(this._selected,t.value);t.blur();this._queue();return;}
      if(t.hasAttribute('data-search-source')&&this._catalog){this._catalog.sourceId=t.value;return;}
      if(t.dataset.kind==='seek'){
        const state=this._hass.states[t.dataset.entity],duration=Number(state?.attributes.media_duration),position=Number(t.value);
        if((Number(state?.attributes.supported_features||0)&2)&&Number.isFinite(duration)&&duration>0&&Number.isFinite(position))this._service(t.dataset.entity,'media_seek',{seek_position:Math.max(0,Math.min(duration,position))});
      }
      if(t.dataset.kind==='number')this._service(t.dataset.entity,'set_value',{value:Number(t.value)});
      if(t.dataset.kind==='select')this._service(t.dataset.entity,'select_option',{option:t.value});
      // Text is saved explicitly, so opening another tab never submits a draft.
      if(t.dataset.kind!=='text')t.blur();
    }
  }
  const STYLE=`
    .status-notice{display:flex;align-items:center;gap:10px;margin:10px 0;padding:12px;border:1px solid var(--divider-color);border-radius:10px;background:var(--secondary-background-color);font-size:12px;line-height:1.6;overflow-wrap:anywhere}.status-notice>span{flex:1;min-width:0}.status-notice>ha-icon{flex-shrink:0;color:var(--warning-color,#e6a23c)}.status-notice.is-error{border-color:var(--error-color);color:var(--error-color)}.status-notice.is-error>ha-icon{color:var(--error-color)}.bt-device.bt-output{border-left:3px solid var(--accent);padding-left:10px}.bt-name .badge{justify-self:start;color:var(--accent)}button.connection{text-align:left;width:100%;font:inherit;cursor:pointer}button.connection:hover{border-color:var(--accent)}
    .bt-device{display:grid;grid-template-columns:24px minmax(0,1fr) auto;gap:10px;align-items:center;padding:12px 0;border-bottom:1px solid var(--divider-color)}.bt-device:last-child{border-bottom:0}.bt-device>ha-icon{color:var(--accent);--mdc-icon-size:22px}.bt-name{min-width:0;display:grid;gap:4px}.bt-name strong{font-size:13px;overflow-wrap:anywhere}.bt-name small{font-size:11px;color:var(--secondary-text-color)}.bt-device button{font-size:12px;padding:8px;white-space:nowrap}
    .room-list{display:grid;gap:10px;margin:16px 0}.room-speaker{border:1px solid var(--divider-color);border-radius:12px;padding:12px}.room-choice{display:flex;align-items:center;gap:10px;margin-bottom:10px}.room-choice input[type=checkbox]{width:18px;height:18px;accent-color:var(--accent)}.room-choice span{display:grid;gap:4px}.room-choice small{font-size:11px}.room-actions{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}
    :host{overflow-anchor:none}
    main.entity-scroll{overflow-anchor:none;scroll-behavior:auto}
    main.entity-scroll{height:var(--vbot-tab-height, min(70vh,800px));overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;scrollbar-gutter:stable;scrollbar-width:thin;scrollbar-color:var(--secondary-text-color) transparent}main.entity-scroll:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}main.entity-scroll::-webkit-scrollbar{width:7px}main.entity-scroll::-webkit-scrollbar-thumb{background:var(--divider-color);border-radius:8px}
    .connection-status{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-bottom:16px}.connection{display:flex;align-items:center;gap:8px;min-width:0;padding:9px 10px;border:1px solid var(--divider-color);border-radius:11px;background:var(--card-background-color)}.connection>ha-icon{--mdc-icon-size:21px;flex-shrink:0;color:var(--secondary-text-color)}.connection>div{min-width:0}.connection strong{display:block;font-size:11px;font-weight:600}.connection span{display:block;font-size:10px;line-height:1.5;color:var(--secondary-text-color);overflow-wrap:anywhere}.connection.connected>ha-icon{color:var(--accent)}.connection.connected{border-color:color-mix(in srgb,var(--accent) 35%,var(--divider-color))}
    .fold-panel>summary{display:flex;align-items:center;gap:8px;cursor:pointer;list-style:none;font-size:14px;font-weight:600}.fold-panel>summary::-webkit-details-marker{display:none}.fold-panel>summary>ha-icon{--mdc-icon-size:21px;color:var(--accent)}.fold-chevron{margin-left:auto;transition:transform .15s}.fold-panel[open]>summary .fold-chevron{transform:rotate(180deg)}.fold-body{padding-top:16px}.library-toolbar{text-align:right}.library-toolbar button{font-size:12px;display:inline-flex;align-items:center;gap:5px}.player-settings{border-top:1px solid var(--divider-color);margin-top:20px;padding-top:4px}.player-settings .row:last-child{border-bottom:0;padding-bottom:0}
    .media-panel{margin-top:20px;border:1px solid var(--divider-color);border-radius:16px;padding:16px}.media-panel h3{display:flex;align-items:center;gap:7px}.media-panel h3 ha-icon{color:var(--accent);--mdc-icon-size:21px}.playlist-picker{display:flex;align-items:center;gap:10px}.playlist-picker select{flex:1;min-width:0}.action-primary{display:flex;align-items:center;justify-content:center;gap:6px;white-space:nowrap;background:var(--accent);color:var(--text-primary-color,#fff);border-color:var(--accent);font-size:12px}.action-primary:hover{background:var(--accent);filter:brightness(1.08)}.action-primary ha-icon{--mdc-icon-size:18px}.media-panel textarea{box-sizing:border-box;width:100%;resize:vertical;border:1px solid var(--divider-color);border-radius:10px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit;font-size:13px;padding:11px;line-height:1.5}.tts-actions{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:10px}.tts-actions .hint{margin:0}@media(max-width:380px){.playlist-picker{align-items:stretch;flex-direction:column}.tts-actions{flex-wrap:wrap}}
    :host{display:block;color:var(--primary-text-color);--accent:var(--primary-color,#03a9f4)}*{box-sizing:border-box}
    ha-card{overflow:hidden;background:var(--ha-card-background,var(--card-background-color));border-radius:var(--ha-card-border-radius,16px)}
    header{display:flex;align-items:center;justify-content:space-between;padding:20px 20px 12px}.brand{display:flex;gap:12px;align-items:center}.brand>ha-icon{color:var(--accent);--mdc-icon-size:34px}h2{margin:0;font-size:20px}small,.muted,.hint,footer{color:var(--secondary-text-color)}
    button,input,select{font:inherit;color:inherit}button{cursor:pointer;background:transparent;border:1px solid var(--divider-color);border-radius:10px;padding:9px 12px}button:hover{background:var(--secondary-background-color)}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}button:disabled,input:disabled,select:disabled{opacity:.45;cursor:not-allowed}
    select,input:not([type=range]){width:100%;padding:9px;border:1px solid var(--divider-color);border-radius:9px;background:var(--card-background-color)}.device{padding:0 20px 16px}.device label{font-size:12px;color:var(--secondary-text-color)}.device select{margin-top:6px;color:var(--primary-text-color)}
    nav{display:flex;border-block:1px solid var(--divider-color);overflow-x:auto}nav button{flex:1;display:flex;gap:5px;align-items:center;justify-content:center;border:0;border-bottom:3px solid transparent;border-radius:0;white-space:nowrap;font-size:13px;padding:13px 9px}nav button[aria-selected=true]{border-color:var(--accent);color:var(--accent)}nav ha-icon{--mdc-icon-size:18px}main{padding:18px 20px}.icon{border:0;padding:8px}.row{display:grid;grid-template-columns:minmax(110px,1fr) minmax(140px,1fr);gap:14px;align-items:center;padding:12px 0;border-bottom:1px solid var(--divider-color)}.label{border:0;text-align:left;padding:0;font-size:13px;overflow-wrap:anywhere}.range,.text{display:flex;align-items:center;gap:8px}.range input{min-width:30px;flex:1}.range output{min-width:54px;text-align:right;font-size:12px}input[type=range]{accent-color:var(--accent);cursor:pointer}.toggle.on{color:var(--accent);border-color:var(--accent)}h3{margin:0 0 12px;font-size:15px}.player{text-align:center;border-radius:14px;padding:20px;background:var(--secondary-background-color);margin-bottom:20px}.speaker{--mdc-icon-size:42px;color:var(--accent);margin-bottom:10px}.player p{color:var(--secondary-text-color);font-size:13px}.transport{display:flex;justify-content:center;gap:12px}.transport button{border:1px solid var(--divider-color);border-radius:50%;padding:12px}.section-title{display:flex;justify-content:space-between;align-items:center;gap:8px}.badge{font-size:11px;padding:5px 8px;border-radius:20px;background:var(--secondary-background-color)}.eq{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px;margin:18px 0}.band{display:flex;flex-direction:column;align-items:center;gap:8px;border:1px solid var(--divider-color);border-radius:12px;padding:12px 2px;min-width:0}.band strong{font-size:12px}.band small{font-size:10px}.vertical{writing-mode:vertical-lr;direction:rtl;appearance:auto;height:170px;width:26px;max-width:100%;margin:4px 0}.value{border:0;font-size:12px;padding:4px;overflow-wrap:anywhere}.hint{font-size:12px;line-height:1.6}.error{padding:12px;border-radius:10px;background:var(--error-color,#db4437);color:white}.empty{font-size:13px;color:var(--secondary-text-color);line-height:1.6}footer{padding:0 20px 16px;font-size:11px}
    .media-extras{margin-top:20px;border:1px solid var(--divider-color);border-radius:14px;padding:14px}.media-extras summary{display:flex;gap:8px;align-items:center;cursor:pointer;font-size:13px;list-style:none}.media-extras summary ha-icon{color:var(--accent);--mdc-icon-size:20px}.media-extras section{margin-top:16px}.media-extras section>h3{font-size:11px;color:var(--secondary-text-color)}
    .player{position:relative;isolation:isolate;overflow:hidden;padding:0;border:1px solid var(--divider-color);border-radius:20px;background:linear-gradient(140deg,var(--secondary-background-color),var(--card-background-color));text-align:left}.art-background{position:absolute;inset:-10%;width:120%;height:120%;object-fit:cover;filter:blur(30px);opacity:.2;z-index:-2;pointer-events:none}.player:after{content:'';position:absolute;inset:0;z-index:-1;background:linear-gradient(180deg,transparent,var(--card-background-color));pointer-events:none}.player-content{padding:20px}.player-top{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:11px;margin-bottom:20px}.playing-state{display:flex;align-items:center;gap:7px}.state-dot{height:7px;width:7px;border-radius:50%;background:var(--secondary-text-color)}.state-dot.live{background:var(--accent);box-shadow:0 0 0 4px color-mix(in srgb,var(--accent) 14%,transparent)}.source-chip{border:1px solid var(--divider-color);border-radius:20px;padding:4px 9px;max-width:50%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.track{display:flex;align-items:center;gap:18px;margin-bottom:20px}.cover{position:relative;display:grid;place-items:center;flex:0 0 112px;width:112px;height:112px;overflow:hidden;border-radius:14px;background:var(--secondary-background-color);box-shadow:0 8px 25px #0002}.cover ha-icon{--mdc-icon-size:44px;color:var(--accent)}.cover img{position:absolute;width:100%;height:100%;object-fit:cover}.track-text{min-width:0}.track-text>small:first-child{font-size:9px;letter-spacing:.16em;color:var(--accent)}.track-text h3{font-size:19px;line-height:1.35;margin:7px 0;overflow-wrap:anywhere}.track-text p{margin:0 0 5px;font-size:13px}.track-text small{font-size:11px}.timeline input{width:100%;height:16px;margin:0}.times{display:flex;justify-content:space-between;gap:10px;font-size:11px;color:var(--secondary-text-color);font-variant-numeric:tabular-nums;margin:5px 0 15px}.transport{align-items:center;gap:14px}.transport .primary-play{background:var(--accent);color:var(--text-primary-color,#fff);border-color:var(--accent);padding:16px;box-shadow:0 5px 16px color-mix(in srgb,var(--accent) 25%,transparent)}.transport .muted-volume{color:var(--error-color)}.playlist-caption{display:flex;align-items:center;justify-content:center;gap:6px;margin-top:16px;font-size:11px;color:var(--secondary-text-color)}.playlist-caption ha-icon{--mdc-icon-size:16px}.quick-controls{display:flex;gap:8px;margin:0 0 24px;flex-wrap:wrap}.quick{display:flex;flex:1;flex-direction:column;align-items:center;justify-content:center;gap:5px;min-width:65px;padding:12px 6px;border-radius:13px;background:var(--secondary-background-color);font-size:11px}.quick ha-icon{--mdc-icon-size:22px}.quick small{font-size:10px}.quick.enabled{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 45%,var(--divider-color))}.library{margin-top:24px;border:1px solid var(--divider-color);border-radius:16px;padding:16px}.library h3{display:flex;align-items:center;gap:7px;margin:0}.library h3 ha-icon{--mdc-icon-size:20px;color:var(--accent)}.search-bar{display:grid;grid-template-columns:minmax(100px,1fr) minmax(150px,2fr);gap:8px;margin:16px 0 10px}.search-query{display:flex;gap:6px}.search-query input{min-width:0}.search-button{padding:8px;background:var(--accent);color:var(--text-primary-color,#fff);border:0}.source-shortcuts{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}.source-shortcuts button{border-radius:20px;font-size:11px;padding:5px 10px}.results{max-height:360px;overflow-y:auto;overscroll-behavior:contain}.result{display:flex;align-items:center;gap:9px;border-top:1px solid var(--divider-color);padding:10px 0}.result-cover{position:relative;display:grid;place-items:center;overflow:hidden;flex:0 0 40px;width:40px;height:40px;border-radius:8px;background:var(--secondary-background-color);color:var(--accent)}.result-cover img{position:absolute;width:100%;height:100%;object-fit:cover}.result-name{flex:1;min-width:0;font-size:12px;overflow-wrap:anywhere;line-height:1.5}.result .icon{padding:5px;flex-shrink:0;color:var(--accent)}.result-title{font-size:12px;color:var(--secondary-text-color);margin:14px 0}.search-error{font-size:12px;color:var(--error-color);line-height:1.6}.back{display:flex;align-items:center;font-size:12px;padding:5px 8px}
    @media(max-width:380px){main{padding:14px 10px}.eq{gap:3px}.band strong{font-size:10px}.band small{font-size:9px}nav button{font-size:11px;gap:3px}.row{grid-template-columns:1fr;gap:8px}.vertical{height:145px}.cover{flex-basis:80px;width:80px;height:80px}.track{gap:12px}.track-text h3{font-size:16px}.player-content{padding:16px}.transport{gap:7px}.transport button{padding:8px}.search-bar{grid-template-columns:1fr}.quick{min-width:56px}}
  `;
  class VBotUltimateCardEditor extends HTMLElement {
    constructor(){
      super();this.attachShadow({mode:'open'});this._devices=[];
      this.shadowRoot.addEventListener('change',e=>{
        if(!e.target.dataset.field)return;
        this._config={...this._config,[e.target.dataset.field]:e.target.value};
        this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this._config},bubbles:true,composed:true}));
      });
    }
    setConfig(config){this._config=config;this._render();}
    set hass(hass){
      this._hass=hass;
      if(!this._requested){
        this._requested=true;
        Promise.all([hass.callWS({type:'config/entity_registry/list'}),hass.callWS({type:'config/device_registry/list'})])
          .then(([e,d])=>{this._devices=discover(e,d,this._hass.states);this._render();}).catch(()=>{});
      }
    }
    _render(){
      if(!this._config)return;
      const id=this._config.device_id||'';
      const choices=this._devices.some(d=>d.id===id)||!id?this._devices:[...this._devices,{id,name:id}];
      this.shadowRoot.innerHTML=`<style>label{display:block;margin:14px 0;color:var(--primary-text-color)}input,select{display:block;width:100%;box-sizing:border-box;margin-top:6px;padding:10px;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:8px}p{font-size:12px;color:var(--secondary-text-color)}</style>
        <label>Tiêu đề<input data-field="title" value="${esc(this._config.title||'VBot Ultimate')}"></label>
        <label>Loa được chọn ban đầu<select data-field="device_id"><option value="">Tự động chọn loa</option>${choices.map(d=>`<option value="${esc(d.id)}" ${d.id===id?'selected':''}>${esc(d.name)}</option>`).join('')}</select></label><p>Thẻ tự nhận entity của loa. Bạn vẫn có thể đổi loa ngay trong thẻ.</p>`;
    }
  }
  if(!customElements.get('vbot-ultimate-card'))customElements.define('vbot-ultimate-card',VBotUltimateCard);
  if(!customElements.get('vbot-ultimate-card-editor'))customElements.define('vbot-ultimate-card-editor',VBotUltimateCardEditor);
  window.customCards=window.customCards||[];
  if(!window.customCards.some(c=>c.type==='vbot-ultimate-card'))window.customCards.push({type:'vbot-ultimate-card',name:'VBot Ultimate Card',description:'Tự khám phá loa · Media · Equalizer · Multiroom · Bluetooth · Điều Khiển · Trạng Thái',preview:true});
})();
