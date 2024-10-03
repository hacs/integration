import{_ as i,n as e,r as t,e as d,t as s,s as o,x as l,T as r,c as n}from"./matter-dashboard-app-Bs2zeWCY.js";import{c as a,f as c}from"./fire_event-D4wM1ZZB.js";import"./prevent_default-dFwBPK3O.js";let m=class extends o{constructor(){super(...arguments),this._loading=!1}render(){return this.client.serverInfo.wifi_credentials_set?l`<md-outlined-text-field label="Pairing code" .disabled="${this._loading}">
      </md-outlined-text-field>
      <br />
      <br />
      <md-outlined-button @click=${this._commissionNode} .disabled="${this._loading}"
        >Commission</md-outlined-button
      >${this._loading?l`<md-circular-progress indeterminate></md-circular-progress>`:r}`:l`<md-outlined-text-field label="SSID" .disabled="${this._loading}">
        </md-outlined-text-field>
        <md-outlined-text-field label="Password" type="password" .disabled="${this._loading}">
        </md-outlined-text-field>
        <br />
        <br />
        <md-outlined-button @click=${this._setWifiCredentials} .disabled="${this._loading}"
          >Set WiFi Credentials</md-outlined-button
        >${this._loading?l`<md-circular-progress indeterminate .visible="${this._loading}"></md-circular-progress>`:r}`}_setWifiCredentials(){const i=this._ssidField.value;if(!i)return void alert("SSID is required");const e=this._passwordField.value;if(e){this._loading=!0;try{this.client.setWifiCredentials(i,e)}catch(i){alert(`Error setting WiFi credentials: \n${i.message}`)}finally{this._loading=!1}}else alert("Password is required")}async _commissionNode(){try{if(!this._pairingCodeField.value)return void alert("Pairing code is required");this._loading=!0;const i=await this.client.commissionWithCode(this._pairingCodeField.value,!1);c(this,"node-commissioned",i)}catch(i){alert(`Error commissioning node: \n${i.message}`)}finally{this._loading=!1}}};i([a({context:n,subscribe:!0}),e({attribute:!1})],m.prototype,"client",void 0),i([t()],m.prototype,"_loading",void 0),i([d("md-outlined-text-field[label='SSID']")],m.prototype,"_ssidField",void 0),i([d("md-outlined-text-field[label='Password']")],m.prototype,"_passwordField",void 0),i([d("md-outlined-text-field[label='Pairing code']")],m.prototype,"_pairingCodeField",void 0),m=i([s("commission-node-wifi")],m);export{m as CommissionNodeWifi};
